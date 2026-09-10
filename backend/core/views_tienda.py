"""API de la fase 5: tienda virtual, carrito y checkout.

Reglas clave:
- Catálogo público: sin autenticación, productos activos agrupados por categoría.
- Carrito: CRUD con validación de stock al agregar/actualizar.
- Cupones: solo vigentes (activo=True, fecha_inicio <= now <= fecha_fin).
- Checkout: reutiliza lógica ACID de VentaPOSView (transaction.atomic + select_for_update).
- Pasarela de pago: mock configurable por variable de entorno (PASARELA_MOCK=True)."""

from decimal import Decimal
import hashlib
import json
import uuid as uuid_mod

from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsPersonal

from . import cache_key

from .models import (Carrito, CarritoItem, Categoria, Cliente, ComentarioProducto,
                     Cupon, DetalleVenta, Empresa, Envio, Favorito, IntentoPago,
                     MovimientoInventario, Producto, Venta)
from .serializers_tienda import (CarritoItemCantidadSerializer, CarritoItemInputSerializer, CarritoSerializer,
                                  CarritoCuponSerializer, CategoriaTiendaSerializer,
                                  ComentarioProductoEscrituraSerializer,
                                  ComentarioProductoSerializer,
                                  CompletarCompradorSerializer, CuponSerializer,
                                  CuponValidarSerializer, FavoritoSerializer,
                                  PedidoCompradorSerializer,
                                  ProductoTiendaSerializer)
from .services import (a_centavos, cobrar, respuesta_desde_transaccion_wompi,
                       secreto_eventos_wompi, validar_firma_webhook_wompi,
                       verificar_transaccion_wompi)


def _obtener_empresa(request):
    return request.user.perfil.empresa


def _limite_paginacion(valor, por_defecto=50, maximo=200):
    """Limite de filas a devolver, acotado a [1, maximo]."""
    try:
        return max(1, min(int(valor), maximo))
    except (TypeError, ValueError):
        return por_defecto


def _registrar_alerta_stock(producto, empresa):
    if not producto.activo:
        return
    if producto.stock > producto.stock_minimo:
        return
    from .notificaciones import crear_notificacion
    crear_notificacion(
        empresa=empresa,
        tipo='stock',
        mensaje=(f"Stock bajo: {producto.nombre} ({producto.sku}) "
                 f"tiene {producto.stock} unidades (minimo {producto.stock_minimo})."),
    )


def _registrar_movimiento(producto, usuario, tipo, cantidad, motivo):
    MovimientoInventario.objects.create(
        producto=producto, usuario=usuario, tipo=tipo,
        cantidad=cantidad, motivo=motivo,
    )
    _registrar_alerta_stock(producto, producto.empresa)


# ------------------------------ Catálogo público -------------------------

class CatalogoPublicoView(APIView):
    """GET lista productos activos (sin auth). Filtros: categoria, busqueda, precio."""
    permission_classes = [AllowAny]

    def get(self, request):
        # Cache corto (60s): el catalogo publico es el endpoint de mayor
        # trafico y no cambia a cada peticion. La clave incluye todos los
        # filtros y la pagina para no servir datos viejos a otros filtros.
        params = request.query_params
        material = (
            params.get('busqueda', '') + '|' + params.get('categoria', '') + '|' +
            params.get('precio_min', '') + '|' + params.get('precio_max', '') + '|' +
            params.get('con_stock', '') + '|' + params.get('orden', '') + '|' +
            params.get('pagina', '1')
        )
        clave = ('cat:' + cache_key.generacion('cat', 'global') + ':' +
                 hashlib.blake2b(material.encode('utf-8'), digest_size=16).hexdigest())
        if cache.get(clave) is not None:
            return Response(cache.get(clave))

        productos = Producto.objects.filter(
            activo=True, deleted_at__isnull=True
        ).select_related('categoria', 'empresa').annotate(
            _promedio_calificacion=Avg('comentarios__calificacion'),
            _total_comentarios=Count('comentarios', distinct=True))

        busqueda = params.get('busqueda', '').strip()
        if busqueda:
            productos = productos.filter(
                Q(nombre__icontains=busqueda)
                | Q(sku__icontains=busqueda)
                | Q(descripcion__icontains=busqueda))

        categoria_id = request.query_params.get('categoria')
        if categoria_id:
            try:
                uuid_mod.UUID(categoria_id)
            except (ValueError, AttributeError, TypeError):
                return Response(
                    {"codigo": "CATEGORIA_INVALIDA",
                     "detalle": "El filtro categoria debe ser un ID valido."},
                    status=status.HTTP_400_BAD_REQUEST)
            productos = productos.filter(categoria__id=categoria_id)

        precio_min = request.query_params.get('precio_min')
        if precio_min:
            try:
                Decimal(precio_min)
            except Exception:
                return Response(
                    {"codigo": "PRECIO_INVALIDO",
                     "detalle": "precio_min debe ser un numero."},
                    status=status.HTTP_400_BAD_REQUEST)
            productos = productos.filter(precio__gte=precio_min)

        precio_max = request.query_params.get('precio_max')
        if precio_max:
            try:
                Decimal(precio_max)
            except Exception:
                return Response(
                    {"codigo": "PRECIO_INVALIDO",
                     "detalle": "precio_max debe ser un numero."},
                    status=status.HTTP_400_BAD_REQUEST)
            productos = productos.filter(precio__lte=precio_max)

        con_stock = request.query_params.get('con_stock')
        if con_stock == 'true':
            productos = productos.filter(stock__gt=0)

        orden = request.query_params.get('orden', 'nombre')
        if orden == 'precio':
            productos = productos.order_by('precio')
        elif orden == '-precio':
            productos = productos.order_by('-precio')
        elif orden == 'reciente':
            productos = productos.order_by('-created_at')
        else:
            productos = productos.order_by('nombre')

        # Paginacion real: 'total' es el conteo completo del filtro, no el
        # tamano de la pagina (antes se cortaba a 50 y se reportaba mal).
        total = productos.count()
        try:
            pagina = max(int(request.query_params.get('pagina', 1)), 1)
        except (TypeError, ValueError):
            pagina = 1
        por_pagina = 24
        inicio = (pagina - 1) * por_pagina
        serializer = ProductoTiendaSerializer(
            productos[inicio:inicio + por_pagina], many=True,
            context={"request": request})

        categorias = Categoria.objects.annotate(
            num_productos=Count('productos', filter=Q(
                productos__activo=True, productos__deleted_at__isnull=True))
        ).filter(num_productos__gt=0).order_by('nombre')

        data = {
            "resultados": serializer.data,
            "total": total,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": max((total + por_pagina - 1) // por_pagina, 1),
            "categorias": CategoriaTiendaSerializer(categorias, many=True).data,
        }
        cache.set(clave, data, 60)
        return Response(data)


class CatalogoProductoDetailView(APIView):
    """GET detalle de un producto público."""
    permission_classes = [AllowAny]

    def get(self, request, id):
        producto = Producto.objects.filter(
            activo=True, deleted_at__isnull=True, id=id
        ).select_related('categoria', 'empresa').annotate(
            _promedio_calificacion=Avg('comentarios__calificacion'),
            _total_comentarios=Count('comentarios', distinct=True)).first()
        if not producto:
            return Response(
                {"codigo": "NO_ENCONTRADO",
                 "detalle": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND)
        return Response(ProductoTiendaSerializer(producto, context={"request": request}).data)


# ---------------------------- Comentarios ----------------------------------

class ComentariosProductoView(APIView):
    """GET lista comentarios de un producto (publico) / POST deja el propio
    (autenticado; si ya comento, actualiza su comentario existente)."""

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, id):
        producto = Producto.objects.filter(
            activo=True, deleted_at__isnull=True, id=id).first()
        if not producto:
            return Response(
                {"codigo": "NO_ENCONTRADO", "detalle": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND)
        # Lista acotada (nunca ilimitada): un producto popular puede acumular
        # miles de comentarios (uno por comprador distinto).
        limite = _limite_paginacion(request.query_params.get('limite', 50))
        comentarios = producto.comentarios.select_related('usuario')[:limite]
        return Response({"resultados": ComentarioProductoSerializer(comentarios, many=True).data})

    def post(self, request, id):
        producto = Producto.objects.filter(
            activo=True, deleted_at__isnull=True, id=id).first()
        if not producto:
            return Response(
                {"codigo": "NO_ENCONTRADO", "detalle": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND)

        entrada = ComentarioProductoEscrituraSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS", "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        comentario, _creado = ComentarioProducto.objects.update_or_create(
            producto=producto, usuario=request.user,
            defaults=entrada.validated_data)
        return Response(ComentarioProductoSerializer(comentario).data,
                        status=status.HTTP_201_CREATED)


# ------------------------------ Favoritos ----------------------------------

class MisFavoritosView(APIView):
    """GET lista los favoritos del usuario autenticado (con el producto).

    Derecho de acceso: el usuario solo ve y manipula SUS propios favoritos.
    No hay aislamiento por empresa porque el marketplace es multi-vendedor:
    un comprador guarda productos de cualquier empresa vendedora."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favoritos = (Favorito.objects.filter(usuario=request.user)
                     .select_related('producto__categoria', 'producto__empresa')
                     .order_by('-created_at'))
        return Response(FavoritoSerializer(favoritos, many=True).data)


class FavoritoToggleView(APIView):
    """POST añade un producto a favoritos / DELETE lo quita (idempotente)."""
    permission_classes = [IsAuthenticated]

    def _producto(self, request, producto_id):
        producto = Producto.objects.filter(
            activo=True, deleted_at__isnull=True, id=producto_id).first()
        if not producto:
            return None
        return producto

    def post(self, request, producto_id):
        producto = self._producto(request, producto_id)
        if not producto:
            return Response(
                {"codigo": "NO_ENCONTRADO", "detalle": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND)

        favorito, creado = Favorito.objects.get_or_create(
            usuario=request.user, producto=producto)
        return Response(
            FavoritoSerializer(favorito).data,
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK)

    def delete(self, request, producto_id):
        producto = self._producto(request, producto_id)
        if not producto:
            return Response(
                {"codigo": "NO_ENCONTRADO", "detalle": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND)

        Favorito.objects.filter(usuario=request.user, producto=producto).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoritoEstadoView(APIView):
    """GET informa si un producto es favorito del usuario autenticado."""
    permission_classes = [IsAuthenticated]

    def get(self, request, producto_id):
        es_favorito = Favorito.objects.filter(
            usuario=request.user, producto_id=producto_id).exists()
        return Response({"producto": str(producto_id), "es_favorito": es_favorito})


# ------------------------------ Cupones ----------------------------------

class CuponesView(APIView):
    """GET lista cupones / POST crea cupón (solo personal autenticado)."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        empresa = _obtener_empresa(request)
        cupones = Cupon.objects.filter(empresa=empresa).order_by('-created_at')
        return Response(CuponSerializer(cupones[:50], many=True).data)

    def post(self, request):
        serializer = CuponSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos del cupon.",
                 "errores": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)

        empresa = _obtener_empresa(request)
        if Cupon.objects.filter(empresa=empresa,
                                codigo=serializer.validated_data['codigo'].upper()).exists():
            return Response(
                {"codigo": "CODIGO_DUPLICADO",
                 "detalle": "Ya existe un cupon con ese codigo."},
                status=status.HTTP_400_BAD_REQUEST)

        cupon = serializer.save(
            empresa=empresa,
            codigo=serializer.validated_data['codigo'].upper()
        )

        ActividadUsuario.registrar(
            request.user, "CUPON_CREADO",
            f"Cupon {cupon.codigo} ({cupon.porcentaje}%)")

        return Response(CuponSerializer(cupon).data,
                        status=status.HTTP_201_CREATED)


class CuponValidarView(APIView):
    """POST valida un cupón (lo retorna si es vigente) para el carrito del
    comprador autenticado.

    Aislamiento multiempresa: un comprador (sin empresa propia) solo puede
    validar cupones de las EMPRESAS VENDEDORAS que estan en su carrito. El
    alcance se deriva del estado del carrito (datos de servidor), nunca de
    un ID/empresa aportado por el cliente. Asi no se puede enumerar ni leer
    cupones de tenants ajenos.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        carrito = _carrito_de(request)

        entrada = CuponValidarSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Debes enviar un codigo.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        codigo = entrada.validated_data['codigo'].upper()

        # Empresas vendedoras presentes en el carrito del comprador.
        empresas_carrito = (carrito.items.select_related("producto")
                            .values_list("producto__empresa_id", flat=True))
        cupon = (Cupon.objects
                 .filter(codigo=codigo, empresa_id__in=empresas_carrito)
                 .first())

        if not cupon:
            return Response(
                {"codigo": "NO_ENCONTRADO",
                 "detalle": "No existe un cupon con ese codigo para tu carrito."},
                status=status.HTTP_404_NOT_FOUND)

        if not cupon.esta_vigente:
            return Response(
                {"codigo": "CUPON_VENCIDO",
                 "detalle": "Este cupon no esta vigente o ya expiro."},
                status=status.HTTP_400_BAD_REQUEST)

        return Response(CuponSerializer(cupon).data)


# ------------------------------ Carrito ----------------------------------

def _carrito_de_usuario(usuario, bloquear=False):
    """Carrito del comprador a partir del usuario.

    Existe como variante de ``_carrito_de`` porque el webhook de la pasarela
    resuelve un pago sin ninguna request del comprador: llega de la pasarela,
    no del navegador. El unico dato de identidad disponible ahi es el usuario
    del ``IntentoPago``.

    Con `bloquear=True` toma SELECT FOR UPDATE sobre la fila del carrito para
    serializar operaciones concurrentes del mismo comprador (agregar items,
    actualizar cantidades o aplicar cupon).

    usuario es OneToOneField: dos peticiones concurrentes del mismo
    comprador sin carrito previo podian pasar ambas el "no existe" y
    chocar en Carrito.objects.create(), la segunda con IntegrityError sin
    capturar (500). get_or_create() resuelve la carrera con su propio
    savepoint interno.
    """
    carrito, _creado = Carrito.objects.get_or_create(
        usuario=usuario, defaults={'empresa': None})
    if bloquear:
        carrito = Carrito.objects.select_for_update().get(pk=carrito.pk)
    if carrito.empresa_id is not None:
        # Se migra un carrito con empresa antigua al modelo de marketplace.
        carrito.empresa = None
        carrito.save(update_fields=['empresa'])
    return carrito


def _carrito_de(request, bloquear=False):
    """Carrito del comprador (marketplace): se identifica por usuario."""
    return _carrito_de_usuario(request.user, bloquear=bloquear)


def _carrito_serializado(carrito):
    """Fase 6: evita N+1 (items -> producto) al serializar el carrito."""
    carrito = (Carrito.objects.select_related("cupon")
               .prefetch_related("items__producto").get(pk=carrito.pk))
    return CarritoSerializer(carrito).data


class CarritoView(APIView):
    """GET retorna el carrito del usuario autenticado."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        carrito = _carrito_de(request)
        return Response(_carrito_serializado(carrito))


class CarritoItemView(APIView):
    """POST agrega un item / PUT actualiza cantidad / DELETE elimina item.

    Marketplace: el comprador puede agregar productos activos de CUALQUIER
    empresa (todas comparten catalogo). El carrito no esta atado a una
    empresa vendedora.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        entrada = CarritoItemInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos del item.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        producto_id = entrada.validated_data['producto']
        cantidad = entrada.validated_data['cantidad']

        # Transaccion unica: el carrito y el producto se bloquean para
        # evitar doble insercion o sobrepasar stock en peticiones
        # simultaneas del mismo comprador.
        with transaction.atomic():
            carrito = _carrito_de(request, bloquear=True)

            producto = Producto.objects.select_for_update().filter(
                activo=True, deleted_at__isnull=True, id=producto_id
            ).first()
            if not producto:
                return Response(
                    {"codigo": "PRODUCTO_NO_ENCONTRADO",
                     "detalle": "El producto no existe o no esta activo."},
                    status=status.HTTP_400_BAD_REQUEST)

            item = CarritoItem.objects.filter(
                carrito=carrito, producto=producto).first()

            if item is None:
                if cantidad > producto.stock:
                    return Response(
                        {"codigo": "STOCK_INSUFICIENTE",
                         "detalle": f"Stock disponible: {producto.stock}."},
                        status=status.HTTP_400_BAD_REQUEST)
                item = CarritoItem.objects.create(
                    carrito=carrito, producto=producto, cantidad=cantidad)
            else:
                nueva_cantidad = item.cantidad + cantidad
                if nueva_cantidad > producto.stock:
                    return Response(
                        {"codigo": "STOCK_INSUFICIENTE",
                         "detalle": f"Stock disponible: {producto.stock}, "
                                    f"en carrito: {item.cantidad}, "
                                    f"intenta agregar: {cantidad}."},
                        status=status.HTTP_400_BAD_REQUEST)
                item.cantidad = nueva_cantidad
                item.save(update_fields=['cantidad'])

        return Response(_carrito_serializado(carrito),
                        status=status.HTTP_201_CREATED)

    def put(self, request, item_id):
        entrada = CarritoItemCantidadSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            carrito = _carrito_de(request, bloquear=True)
            item = CarritoItem.objects.select_for_update().filter(
                id=item_id, carrito=carrito).first()
            if not item:
                return Response(
                    {"codigo": "ITEM_NO_ENCONTRADO",
                     "detalle": "El item no existe en tu carrito."},
                    status=status.HTTP_404_NOT_FOUND)

            producto = Producto.objects.select_for_update().filter(
                id=item.producto_id
            ).first()

            nueva_cantidad = entrada.validated_data['cantidad']
            stock = producto.stock if producto else 0
            if nueva_cantidad > stock:
                return Response(
                    {"codigo": "STOCK_INSUFICIENTE",
                     "detalle": f"Stock disponible: {stock}."},
                    status=status.HTTP_400_BAD_REQUEST)

            item.cantidad = nueva_cantidad
            item.save(update_fields=['cantidad'])

        return Response(_carrito_serializado(carrito))

    def delete(self, request, item_id):
        carrito = _carrito_de(request)
        item = CarritoItem.objects.filter(
            id=item_id, carrito=carrito).first()
        if not item:
            return Response(
                {"codigo": "ITEM_NO_ENCONTRADO",
                 "detalle": "El item no existe en tu carrito."},
                status=status.HTTP_404_NOT_FOUND)

        item.delete()
        return Response(_carrito_serializado(carrito))


class CarritoCuponView(APIView):
    """POST aplica un cupón al carrito / DELETE lo quita.

    Un cupón pertenece a la empresa vendedora que lo emite. Solo puede
    aplicarse si TODOS los items del carrito son de esa empresa.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        entrada = CarritoCuponSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Envia el ID del cupon.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            carrito = _carrito_de(request, bloquear=True)

            cupon_id = entrada.validated_data.get('cupon_id')
            if not cupon_id:
                carrito.cupon = None
                carrito.save(update_fields=['cupon'])
                return Response(_carrito_serializado(carrito))

            # Aislamiento multiempresa: el cupon solo puede pertenecer a una
            # empresa vendedora que este efectivamente en el carrito. El alcance
            # se deriva de los productos del carrito (datos de servidor), nunca
            # de un ID/empresa aportado por el cliente.
            items = carrito.items.select_related('producto').all()
            if not items:
                return Response(
                    {"codigo": "CARRITO_VACIO",
                     "detalle": "Tu carrito esta vacio."},
                    status=status.HTTP_400_BAD_REQUEST)

            empresas_carrito = {i.producto.empresa_id for i in items
                                if i.producto.empresa_id is not None}
            cupon = (Cupon.objects
                     .filter(id=cupon_id, empresa_id__in=empresas_carrito)
                     .first())
            if not cupon or not cupon.esta_vigente:
                return Response(
                    {"codigo": "CUPON_NO_ENCONTRADO",
                     "detalle": "El cupon no existe o no esta vigente."},
                    status=status.HTTP_404_NOT_FOUND)

            # El cupon aplica solo si TODOS los items del carrito son de la
            # empresa que lo emite (regla del marketplace).
            if any(i.producto.empresa_id != cupon.empresa_id for i in items):
                return Response(
                    {"codigo": "CUPON_NO_APLICA",
                     "detalle": "El cupon solo aplica si todos los productos "
                                "del carrito son de la empresa que lo emite."},
                    status=status.HTTP_400_BAD_REQUEST)

            carrito.cupon = cupon
            carrito.save(update_fields=['cupon'])

            return Response(_carrito_serializado(carrito))

    def delete(self, request):
        carrito = _carrito_de(request)
        if carrito.cupon:
            carrito.cupon = None
            carrito.save(update_fields=['cupon'])
        return Response(_carrito_serializado(carrito))


# -------------------- Resolucion de un intento de pago --------------------
#
# Un cobro se resuelve por dos caminos que hacen exactamente lo mismo:
#
# - Sincrono: la pasarela responde 'aprobado'/'rechazado' en el propio POST de
#   checkout (es el caso del mock).
# - Asincrono: la pasarela responde 'pendiente' y el resultado llega despues
#   por webhook, sin request del comprador (es el caso de Wompi).
#
# Por eso confirmar y revertir viven aqui, a nivel de modulo y tomando el
# ``IntentoPago`` en vez de la request: si cada camino tuviera su copia, un
# arreglo en uno se olvidaria en el otro y el stock quedaria descuadrado.
#
# Las dos funciones son idempotentes: bloquean el intento y solo actuan si
# sigue 'pendiente'. Es un requisito duro, no una precaucion: las pasarelas
# reenvian el mismo webhook varias veces hasta recibir un 2xx, y confirmar dos
# veces descontaria el stock o cerraria el carrito dos veces.

def _resolver_intento_bloqueado(intento):
    """Recarga el intento con SELECT FOR UPDATE. None si ya no esta pendiente.

    Debe llamarse dentro de un ``transaction.atomic()``.
    """
    actual = IntentoPago.objects.select_for_update().filter(
        pk=intento.pk).first()
    if actual is None or actual.estado != 'pendiente':
        return None
    return actual


def _confirmar_intento(intento, resultado):
    """Confirma el pago de un intento: ventas pagadas y carrito vaciado.

    Devuelve la lista de ventas confirmadas, o None si el intento ya estaba
    resuelto (reintento del webhook, doble checkout).
    """
    with transaction.atomic():
        intento = _resolver_intento_bloqueado(intento)
        if intento is None:
            return None

        # Solo las ventas reservadas por ESTE intento: filtrar por usuario y
        # estado barreria tambien pendientes de checkouts anteriores y las
        # marcaria pagadas con una transaccion que no les corresponde.
        ventas = list(Venta.objects.filter(
            intento_pago=intento,
            estado_pago='pendiente',
        ).order_by('created_at'))
        for v in ventas:
            v.estado = 'completada'
            v.estado_pago = 'aprobado'
            v.pasarela = resultado.pasarela
            v.transaccion_id = resultado.transaccion_id
            v.pagado_en = timezone.now()
            v.save(update_fields=[
                'estado', 'estado_pago', 'pasarela',
                'transaccion_id', 'pagado_en',
            ])

        intento.estado = 'aprobado'
        intento.transaccion_id = resultado.transaccion_id
        intento.pasarela = resultado.pasarela
        intento.respuesta_cruda = json.dumps(resultado.crudo, default=str)
        intento.save(update_fields=[
            'estado', 'transaccion_id', 'pasarela', 'respuesta_cruda'])

        # El carrito solo se vacia al confirmar el cobro: si el pago se cae,
        # el comprador conserva su carrito para reintentar.
        carrito = _carrito_de_usuario(intento.usuario, bloquear=True)
        carrito.items.all().delete()
        carrito.cupon = None
        carrito.save(update_fields=['cupon'])

        ActividadUsuario.registrar(
            intento.usuario, "CHECKOUT_MARKETPLACE",
            f"{len(ventas)} venta(s) aprobada(s) - Total "
            f"${sum(v.total for v in ventas)} - {resultado.transaccion_id}")

    return ventas


def _revertir_intento(intento, resultado):
    """Revierte la reserva de stock de un pago no aprobado (Fase 2).

    - Restaura las unidades reservadas de cada producto.
    - Registra un movimiento de reversion (entrada) por cada linea.
    - Marca las ventas pendientes como estado_pago 'reversado' (auditoria,
      NO cobrables; no cuentan en analitica ni en total_compras).
    - NO vacia el carrito: el comprador puede reintentar o modificar.

    Devuelve la lista de ventas revertidas, o None si el intento ya estaba
    resuelto.
    """
    with transaction.atomic():
        intento = _resolver_intento_bloqueado(intento)
        if intento is None:
            return None

        # Acotado al intento por el mismo motivo que la confirmacion: revertir
        # por usuario+estado devolveria stock de ventas de otros checkouts.
        ventas = list(Venta.objects.filter(
            intento_pago=intento,
            estado='pendiente',
            estado_pago='pendiente',
        ))
        for v in ventas:
            for detalle in v.detalles.select_related('producto'):
                p = detalle.producto
                p.stock += detalle.cantidad
                p.save(update_fields=['stock'])
                _registrar_movimiento(
                    p, intento.usuario, 'entrada', detalle.cantidad,
                    f"Reversion pago rechazado {v.numero_factura}")
            v.estado = 'pendiente'
            v.estado_pago = 'reversado'
            v.save(update_fields=['estado', 'estado_pago'])

        intento.estado = 'rechazado'
        intento.transaccion_id = resultado.transaccion_id
        intento.pasarela = resultado.pasarela
        intento.respuesta_cruda = json.dumps(resultado.crudo, default=str)
        intento.save(update_fields=[
            'estado', 'transaccion_id', 'pasarela', 'respuesta_cruda'])

    return ventas


def _ventas_serializadas(ventas):
    """Resumen de ventas para las respuestas de checkout y estado de pago."""
    return [{
        "venta_id": str(v.id),
        "numero_factura": v.numero_factura,
        "empresa_id": str(v.empresa_id),
        "empresa_nombre": v.empresa.nombre,
        "total": str(v.total),
    } for v in ventas]


# ------------------------------ Checkout ---------------------------------

class CheckoutView(APIView):
    """POST convierte el carrito en ventas (checkout tipo marketplace).

    El carrito puede llevar productos de varias empresas. Se genera UNA
    venta por cada empresa vendedora.

Flujo (Fase 2 - reservar -> cobrar -> confirmar) en TRES tramos:

    1. RESERVA (transaction.atomic con locks cortos):
       valida stock de cada item con select_for_update; si hay stock
       insuficiente rechaza SIN cobrar ni tocar la pasarela. Crea las ventas
       en estado 'pendiente' / estado_pago 'pendiente', descuenta stock y
       registra los movimientos. NO vacia el carrito todavia. Termina y suelta
       los locks ANTES de llamar a la pasarela: asi no se mantiene ningun lock
       durante la latencia de un proveedor real.

    2. COBRO (FUERA de cualquier transaction.atomic y de los locks):
       llama al adaptador de pasarela (mock hoy). Una llamada de red a un
       proveedor externo nunca debe ejecutarse con filas bloqueadas por
       select_for_update, porque el lock quedaria tomado todo el tiempo de
       latencia del proveedor. Por eso la reserva y la confirmacion son dos
       transacciones separadas y el cobro corre entre ambas, sin locks.

    3. CONFIRMACION (transaction.atomic):
       - aprobado: ventas -> estado 'completada' / estado_pago 'aprobado',
         se fijan pasarela, transaccion_id y pagado_en; se vacia el carrito.
       - rechazado: se revierte la reserva (stock y movimientos), las ventas
         quedan estado_pago 'reversado' (registro de auditoria, NO cobrable),
         el carrito NO se vacia y se responde 402 PAGO_RECHAZADO.

    Idempotencia (Fase 3): el checkout acepta una 'idempotencia_clave'. Si ya
    existe un IntentoPago con esa clave y resolucion, se devuelve el resultado
    previo sin volver a cobrar (no se duplica el cobro ni la venta).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        metodo_pago = request.data.get('metodo_pago', 'tarjeta')
        if metodo_pago not in dict(Venta.METODO_PAGO_CHOICES):
            return Response(
                {"codigo": "METODO_PAGO_INVALIDO",
                 "detalle": "Metodo de pago no valido.",
                 "opciones": [c for c, _ in Venta.METODO_PAGO_CHOICES]},
                status=status.HTTP_400_BAD_REQUEST)

# Clave de idempotencia: la aporta el cliente o se deriva del contenido
        # del carrito, de modo que un checkout reintentado no cobre dos veces.
        idempotencia_clave = (request.data.get('idempotencia_clave', '')
                              or self._clave_de_carrito(request))

        # ---------------- 0. Deduplicacion por clave ----------------
        # Solo cortamos (sin volver a cobrar) cuando el intento previo con la
        # misma clave ya fue APROBADO: asi un reintento no cobra ni crea venta
        # dos veces. Un pago rechazado/pendiente permite reintentar (Fase 2:
        # el carrito NO se vacia y el comprador puede corregir el metodo).
        intento_previo = IntentoPago.objects.filter(
            usuario=request.user, idempotencia_clave=idempotencia_clave,
        ).first()
        if intento_previo and intento_previo.estado == 'aprobado':
            return self._respuesta_desde_intento(intento_previo)

        # ---------------- 1. Reserva (locks cortos) ----------------
        referencias_empresa = []

        with transaction.atomic():
            carrito = _carrito_de(request, bloquear=True)

            if not carrito.items.exists():
                return Response(
                    {"codigo": "CARRITO_VACIO",
                     "detalle": "Tu carrito esta vacio."},
                    status=status.HTTP_400_BAD_REQUEST)

            cliente = Cliente.objects.filter(
                usuario=request.user, deleted_at__isnull=True
            ).first()
            if not cliente:
                return Response(
                    {"codigo": "SIN_CLIENTE",
                     "detalle": "Completa tus datos de comprador "
                                "(Registrate como cliente) para poder comprar."},
                    status=status.HTTP_400_BAD_REQUEST)

            # Cada venta del marketplace genera un Envio (fase 10): sin
            # direccion/ciudad no hay a donde despachar, se rechaza antes de
            # tocar stock (mismo criterio que SIN_CLIENTE: pedir el dato
            # faltante en vez de crear un envio inutilizable).
            if not cliente.direccion.strip() or not cliente.ciudad.strip():
                return Response(
                    {"codigo": "SIN_DIRECCION_ENVIO",
                     "detalle": "Completa tu direccion y ciudad de envio "
                                "antes de finalizar la compra."},
                    status=status.HTTP_400_BAD_REQUEST)

            items = list(carrito.items.select_related('producto').all())

            fallidos = []
            for item in items:
                producto = Producto.objects.select_for_update().filter(
                    id=item.producto.id, deleted_at__isnull=True
                ).first()
                if not producto:
                    fallidos.append({
                        'producto': str(item.producto.id),
                        'producto_nombre': 'No encontrado',
                        'solicitado': item.cantidad,
                        'disponible': 0,
                    })
                    continue
                if not producto.activo:
                    fallidos.append({
                        'producto': str(producto.id),
                        'producto_nombre': producto.nombre,
                        'solicitado': item.cantidad,
                        'disponible': 0,
                    })
                    continue
                if producto.stock < item.cantidad:
                    fallidos.append({
                        'producto': str(producto.id),
                        'producto_nombre': producto.nombre,
                        'solicitado': item.cantidad,
                        'disponible': producto.stock,
                    })
                    continue
                item.producto = producto

            if fallidos:
                # La pasarela NUNCA fue llamada (stock agotado).
                return Response(
                    {"codigo": "STOCK_INSUFICIENTE",
                     "detalle": "Algunos productos no tienen stock suficiente.",
                     "productos": fallidos},
                    status=status.HTTP_400_BAD_REQUEST)

            # Agrupar por empresa vendedora
            por_vendedor = {}
            for item in items:
                por_vendedor.setdefault(item.producto.empresa_id, []).append(item)

            cupon = carrito.cupon if (carrito.cupon and carrito.cupon.esta_vigente) else None
            monto_total = Decimal('0')

            # Serializacion de la reserva por clave de idempotencia: se bloquea
            # el carrito (select_for_update) al inicio. Dos checkouts
            # concurrentes del MISMO carrito quedan serializados por ese lock.
            # Al entrar el segundo tras el commit del primero, detecta si ya
            # existe un IntentoPago para esta clave y actua en consecuencia.
            intento = IntentoPago.objects.filter(
                usuario=request.user,
                idempotencia_clave=idempotencia_clave,
            ).first()
            if intento:
                if intento.estado == 'aprobado':
                    return self._respuesta_desde_intento(intento)
                if intento.estado == 'pendiente':
                    # Ya hay un cobro en curso con esta misma clave: no se
                    # reserva de nuevo ni se vuelve a cobrar.
                    return Response(
                        {"codigo": "PAGO_EN_CURSO",
                         "detalle": "Ya hay un pago en proceso para este "
                                    "carrito. Espera unos segundos."},
                        status=status.HTTP_409_CONFLICT)
                # estado 'rechazado': reintento legitimo -> volver a intentar.
                intento.estado = 'pendiente'
                intento.save(update_fields=['estado'])
            else:
                intento = IntentoPago.objects.create(
                    usuario=request.user,
                    idempotencia_clave=idempotencia_clave,
                    monto_total=Decimal('0'),
                    moneda='COP',
                    estado='pendiente',
                )

            for empresa_id, lineas in por_vendedor.items():
                empresa = Empresa.objects.select_for_update().filter(
                    pk=empresa_id).first()
                subtotal = sum(
                    Decimal(str(item.producto.precio)) * item.cantidad
                    for item in lineas
                )
                descuento = Decimal('0')
                if cupon and cupon.empresa_id == empresa_id:
                    descuento = subtotal * cupon.porcentaje / Decimal('100')
                total = max(subtotal - descuento, Decimal('0'))
                monto_total += total

                venta = Venta.objects.create(
                    empresa=empresa,
                    cliente=cliente,
                    vendedor=request.user,
                    subtotal=subtotal,
                    descuento=descuento,
                    total=total,
estado='pendiente',          # se confirma al cobrar
                    estado_pago='pendiente',     # se confirma al cobrar
                    metodo_pago=metodo_pago,
                    intento_pago=intento,
                    notas=("Checkout tienda"
                           + (f" - Cupon: {cupon.codigo}" if cupon and cupon.empresa_id == empresa_id else '')),
                )

                # Reserva de stock: se resta ya (sin esto un segundo checkout
                # concurrente podria vender lo mismo mientras se espera la
                # pasarela); si el pago se rechaza, la transaccion B lo revierte.
                for item in lineas:
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=item.producto,
                        cantidad=item.cantidad,
                        precio_unitario=item.producto.precio,
                    )
                    item.producto.stock -= item.cantidad
                    item.producto.save(update_fields=['stock'])
                    _registrar_movimiento(
                        item.producto, request.user, 'salida', item.cantidad,
                        f"Reserva checkout tienda {venta.numero_factura}")

                Envio.objects.create(
                    venta=venta,
                    direccion=cliente.direccion,
                    ciudad=cliente.ciudad,
                )

                referencias_empresa.append(
                    f"{empresa.nombre}:{venta.numero_factura}")

            # Persistimos el monto real de la reserva en el intento ya creado.
            intento.monto_total = monto_total
            intento.save(update_fields=['monto_total'])



        # ---------------- 2. Cobro (FUERA de locks) ----------------
        try:
            resultado = cobrar(
                monto=monto_total,
                moneda='COP',
                metodo_pago=metodo_pago,
                referencia="|".join(referencias_empresa),
                idempotencia_clave=idempotencia_clave,
            )
        except Exception:  # pragma: no cover - defensivo
            return Response(
                {"codigo": "PAGO_ERROR",
                 "detalle": "No se pudo procesar el pago. Intenta de nuevo."},
                status=status.HTTP_502_BAD_GATEWAY)

        # ------- 3. Pendiente / Confirmacion / Reversion -------
        if resultado.estado == 'pendiente':
            # Pasarela asincrona (Wompi): el cobro lo completa el comprador en
            # el Web Checkout y el resultado llega despues por webhook. Aqui NO
            # se toca nada: la reserva de stock se mantiene, el intento sigue
            # 'pendiente' (un segundo checkout con la misma clave recibe 409) y
            # el carrito no se vacia hasta que el webhook confirme el cobro.
            return Response({
                "codigo": "PAGO_PENDIENTE",
                "detalle": resultado.mensaje,
                "referencia": idempotencia_clave,
                "total": str(monto_total),
                "pasarela": resultado.pasarela,
                "datos_checkout": resultado.datos_checkout,
            }, status=status.HTTP_202_ACCEPTED)

        if not resultado.aprobada:
            _revertir_intento(intento, resultado)
            return Response(
                {"codigo": "PAGO_RECHAZADO",
                 "detalle": resultado.mensaje},
                status=status.HTTP_402_PAYMENT_REQUIRED)

        ventas = _confirmar_intento(intento, resultado)
        if ventas is None:
            # Otro request (o un webhook) resolvio este intento mientras se
            # cobraba: no se confirma dos veces, se devuelve lo ya registrado.
            intento.refresh_from_db()
            return self._respuesta_desde_intento(intento)

        return Response({
            "codigo": "EXITO",
            "detalle": "Compra realizada exitosamente.",
            "ventas": _ventas_serializadas(ventas),
            "total": str(sum(v.total for v in ventas)),
            "transaccion_id": resultado.transaccion_id,
        }, status=status.HTTP_201_CREATED)

    @staticmethod
    def _clave_de_carrito(request):
        """Deriva una clave de idempotencia estable a partir del carrito.

        Combina el usuario y un hash del contenido (producto|cantidad|cupon),
        de modo que dos checkouts con exactamente el mismo contenido comparten
        clave (deduplicacion), y al cambiar el carrito cambia la clave.
        """
        carrito = _carrito_de(request)
        items = sorted(
            (str(i.producto_id), i.cantidad) for i in carrito.items.all())
        cupon = str(carrito.cupon_id) if carrito.cupon_id else ''
        material = f"{request.user.id}|{items}|{cupon}"
        return hashlib.sha256(material.encode('utf-8')).hexdigest()[:32]

    def _respuesta_desde_intento(self, intento):
        """Reutiliza el resultado de un intento ya resuelto (idempotencia)."""
        if intento.estado == 'aprobado':
            # Por intento, no por transaccion_id: es la relacion explicita y
            # no depende de que la pasarela haya devuelto un id.
            ventas = list(Venta.objects.filter(intento_pago=intento)
                          .select_related('empresa').order_by('created_at'))
            return Response({
                "codigo": "EXITO",
                "detalle": "Compra ya registrada (checkout reiterado).",
                "ventas": _ventas_serializadas(ventas),
                "total": str(sum(v.total for v in ventas)),
                "transaccion_id": intento.transaccion_id,
            }, status=status.HTTP_200_OK)
        return Response(
            {"codigo": "PAGO_RECHAZADO",
             "detalle": "El pago fue rechazado previamente."},
            status=status.HTTP_402_PAYMENT_REQUIRED)


# --------------------- Webhook y estado del pago (Fase 4) -----------------

class WebhookPagoWompiView(APIView):
    """POST endpoint publico donde Wompi notifica ``transaction.updated``.

    Es el unico camino por el que un pago real pasa a 'aprobado'. El comprador
    nunca lo toca: cuando vuelve del Web Checkout solo consulta el estado.
    Confiar en el retorno del navegador seria confiar en el cliente, y
    cualquiera podria darse por pagado manipulando la URL de vuelta.

    Controles, en orden:

    1. Sin ``WOMPI_EVENTS_SECRET`` configurado se responde 503 y no se procesa
       nada. Un webhook sin secreto es un endpoint publico que marca ventas
       como pagadas: es preferible caerse a aceptar eventos sin firmar.
    2. Se valida la firma del evento contra ese secreto. Sin firma valida, 401.
    3. Se reconsulta la transaccion a la API de Wompi. La firma solo cubre los
       campos de ``signature.properties``, asi que el resto del cuerpo no es de
       fiar; la respuesta de la API si lo es. Si la reconsulta no esta
       disponible se usa el cuerpo ya validado.
    4. Se compara el monto cobrado con el reservado. Si no cuadra no se
       confirma nada: se prefiere dejar la venta pendiente y revisarla a mano
       antes que entregar mercancia por un monto que no corresponde.

    Siempre responde 200 en los casos que un reintento no arreglaria (evento
    de otro tipo, referencia desconocida, intento ya resuelto): Wompi reintenta
    mientras no reciba 2xx y no tiene sentido hacerlo repetir un evento que ya
    esta atendido.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        secreto = secreto_eventos_wompi()
        if not secreto:
            return Response(
                {"codigo": "WEBHOOK_NO_CONFIGURADO",
                 "detalle": "Falta WOMPI_EVENTS_SECRET en el servidor."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        evento = request.data if isinstance(request.data, dict) else {}
        checksum = ((evento.get('signature') or {}).get('checksum')
                    or request.headers.get('X-Event-Checksum', ''))
        if not validar_firma_webhook_wompi(evento, secreto, str(checksum)):
            return Response(
                {"codigo": "FIRMA_INVALIDA",
                 "detalle": "La firma del evento no es valida."},
                status=status.HTTP_401_UNAUTHORIZED)

        if evento.get('event') != 'transaction.updated':
            return Response(
                {"codigo": "EVENTO_IGNORADO", "detalle": "Evento no aplicable."},
                status=status.HTTP_200_OK)

        transaccion = (evento.get('data') or {}).get('transaction') or {}
        referencia = str(transaccion.get('reference', ''))
        intento = IntentoPago.objects.filter(
            idempotencia_clave=referencia).first()
        if intento is None:
            # No hay a que aplicarlo. Reintentar no lo arreglaria.
            return Response(
                {"codigo": "REFERENCIA_DESCONOCIDA",
                 "detalle": "No hay un intento de pago con esa referencia."},
                status=status.HTTP_200_OK)

        # Fuente autoritativa: la API de Wompi. Si no responde (sin
        # credenciales o red caida) se usa el cuerpo, que ya paso la firma.
        transaccion_id = str(transaccion.get('id', ''))
        verificada = (verificar_transaccion_wompi(transaccion_id)
                      if transaccion_id else None)
        resultado = verificada or respuesta_desde_transaccion_wompi(transaccion)
        datos = resultado.crudo if isinstance(resultado.crudo, dict) else {}

        recibido = datos.get('amount_in_cents', transaccion.get('amount_in_cents'))
        if recibido is not None:
            try:
                cuadra = int(recibido) == a_centavos(intento.monto_total)
            except (TypeError, ValueError):
                cuadra = False
            if not cuadra:
                return Response(
                    {"codigo": "MONTO_NO_COINCIDE",
                     "detalle": "El monto notificado no coincide con la reserva.",
                     "esperado_centavos": a_centavos(intento.monto_total),
                     "recibido_centavos": recibido},
                    status=status.HTTP_409_CONFLICT)

        if resultado.estado == 'pendiente':
            # Wompi tambien notifica transiciones intermedias. No se resuelve
            # la venta hasta que el estado sea definitivo.
            return Response(
                {"codigo": "PAGO_PENDIENTE",
                 "detalle": "La transaccion sigue en curso."},
                status=status.HTTP_200_OK)

        if resultado.aprobada:
            ventas = _confirmar_intento(intento, resultado)
            codigo = "PAGO_CONFIRMADO"
        else:
            ventas = _revertir_intento(intento, resultado)
            codigo = "PAGO_REVERSADO"

        if ventas is None:
            return Response(
                {"codigo": "YA_PROCESADO",
                 "detalle": "Este intento de pago ya estaba resuelto."},
                status=status.HTTP_200_OK)

        return Response(
            {"codigo": codigo, "ventas": len(ventas),
             "transaccion_id": resultado.transaccion_id},
            status=status.HTTP_200_OK)


class EstadoPagoView(APIView):
    """GET estado de un intento de pago del comprador autenticado.

    Lo consulta el frontend cuando el comprador vuelve del Web Checkout, en
    lugar de leer el resultado de la URL de retorno: el estado real lo fija el
    webhook, no el navegador.

    Siempre acotado a ``usuario=request.user``: nadie puede consultar el pago
    de otro comprador pasando una referencia ajena.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        referencia = request.query_params.get('referencia', '').strip()
        intentos = IntentoPago.objects.filter(usuario=request.user)
        if referencia:
            intentos = intentos.filter(idempotencia_clave=referencia)
        intento = intentos.order_by('-created_at').first()
        if intento is None:
            return Response(
                {"codigo": "NO_ENCONTRADO",
                 "detalle": "No hay un intento de pago con esa referencia."},
                status=status.HTTP_404_NOT_FOUND)

        ventas = list(Venta.objects.filter(intento_pago=intento)
                      .select_related('empresa').order_by('created_at'))
        return Response({
            "codigo": "OK",
            "referencia": intento.idempotencia_clave,
            "estado": intento.estado,
            "pasarela": intento.pasarela,
            "transaccion_id": intento.transaccion_id,
            "total": str(intento.monto_total),
            "ventas": _ventas_serializadas(ventas),
        })


# ------------------------------ Pedidos del comprador ---------------------

class MisPedidosView(APIView):
    """GET historial de compras del comprador autenticado (todas las
    empresas vendedoras que le hayan facturado)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cliente = Cliente.objects.filter(
            usuario=request.user, deleted_at__isnull=True
        ).first()
        if not cliente:
            return Response({"resultados": [], "total": 0})

        pedidos = (Venta.objects.filter(cliente=cliente)
                   .select_related('empresa', 'envio')
                   .prefetch_related('detalles__producto')
                   .order_by('-created_at'))
        # Lista acotada (nunca ilimitada).
        limite = _limite_paginacion(request.query_params.get('limite', 50))
        datos = PedidoCompradorSerializer(pedidos[:limite], many=True).data
        return Response({"resultados": datos, "total": len(datos)})


class CompletarCompradorView(APIView):
    """Vincula al usuario autenticado (admin, empleado o cliente) con un
    Cliente del marketplace, sin exigirle crear otra cuenta. Se llama cuando
    el checkout responde SIN_CLIENTE: solo pide documento y direccion de
    envio, el resto de datos ya existen en su cuenta."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cliente = Cliente.objects.filter(usuario=request.user, deleted_at__isnull=True).first()
        if cliente:
            # Ya tiene datos de comprador: solo se permite completar la
            # direccion de envio si sigue vacia (el checkout la exige).
            if cliente.direccion.strip() and cliente.ciudad.strip():
                return Response(
                    {"codigo": "CLIENTE_EXISTENTE", "detalle": "Ya tienes datos de comprador registrados."},
                    status=status.HTTP_409_CONFLICT)
            direccion = (request.data.get('direccion') or '').strip()
            ciudad = (request.data.get('ciudad') or '').strip()
            if not direccion or not ciudad:
                return Response(
                    {"codigo": "DATOS_INVALIDOS",
                     "detalle": "Completa tu direccion y ciudad de envio.",
                     "errores": {"direccion": ["Obligatoria."], "ciudad": ["Obligatoria."]}},
                    status=status.HTTP_400_BAD_REQUEST)
            cliente.direccion = direccion
            cliente.ciudad = ciudad
            cliente.save(update_fields=['direccion', 'ciudad'])
            return Response({"detalle": "Direccion de envio actualizada."},
                            status=status.HTTP_200_OK)

        entrada = CompletarCompradorSerializer(data=request.data, context={"usuario": request.user})
        if not entrada.is_valid():
            return Response({"codigo": "DATOS_INVALIDOS", "detalle": "Revisa los datos del formulario.",
                             "errores": entrada.errors}, status=status.HTTP_400_BAD_REQUEST)
        entrada.save()
        return Response(status=status.HTTP_201_CREATED)
