"""API de la fase 5: tienda virtual, carrito y checkout.

Reglas clave:
- Catálogo público: sin autenticación, productos activos agrupados por categoría.
- Carrito: CRUD con validación de stock al agregar/actualizar.
- Cupones: solo vigentes (activo=True, fecha_inicio <= now <= fecha_fin).
- Checkout: reutiliza lógica ACID de VentaPOSView (transaction.atomic + select_for_update).
- Pasarela de pago: mock configurable por variable de entorno (PASARELA_MOCK=True)."""

from decimal import Decimal
import os
import uuid as uuid_mod

from django.db import models, transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsPersonal

from .models import (Carrito, CarritoItem, Categoria, Cliente, Cupon,
                     DetalleVenta, Empresa, MovimientoInventario, Notificacion,
                     Producto, Venta)
from .serializers_tienda import (CarritoItemInputSerializer, CarritoSerializer,
                                  CarritoCuponSerializer, CategoriaTiendaSerializer,
                                  CuponSerializer, CuponValidarSerializer,
                                  PedidoCompradorSerializer, ProductoTiendaSerializer)


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
        productos = Producto.objects.filter(
            activo=True, deleted_at__isnull=True
        ).select_related('categoria')

        busqueda = request.query_params.get('busqueda', '').strip()
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
            productos[inicio:inicio + por_pagina], many=True)

        categorias = Categoria.objects.annotate(
            num_productos=Count('productos', filter=Q(
                productos__activo=True, productos__deleted_at__isnull=True))
        ).filter(num_productos__gt=0).order_by('nombre')

        return Response({
            "resultados": serializer.data,
            "total": total,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": max((total + por_pagina - 1) // por_pagina, 1),
            "categorias": CategoriaTiendaSerializer(categorias, many=True).data,
        })


class CatalogoProductoDetailView(APIView):
    """GET detalle de un producto público."""
    permission_classes = [AllowAny]

    def get(self, request, id):
        producto = Producto.objects.filter(
            activo=True, deleted_at__isnull=True, id=id
        ).select_related('categoria').first()
        if not producto:
            return Response(
                {"codigo": "NO_ENCONTRADO",
                 "detalle": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND)
        return Response(ProductoTiendaSerializer(producto).data)


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

def _carrito_de(request, bloquear=False):
    """Carrito del comprador (marketplace): se identifica por usuario.

    Con `bloquear=True` toma SELECT FOR UPDATE sobre la fila del carrito para
    serializar operaciones concurrentes del mismo comprador (agregar items,
    actualizar cantidades o aplicar cupon).
    """
    qs = Carrito.objects.select_for_update() if bloquear else Carrito.objects
    carrito = qs.filter(usuario=request.user).first()
    if carrito is None:
        carrito = Carrito.objects.create(usuario=request.user, empresa=None)
    elif carrito.empresa_id is not None:
        # Se migra un carrito con empresa antigua al modelo de marketplace.
        carrito.empresa = None
        carrito.save(update_fields=['empresa'])
    return carrito


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
        entrada = CarritoItemInputSerializer(data=request.data)
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


# ------------------------------ Checkout ---------------------------------

class CheckoutView(APIView):
    """POST convierte el carrito en ventas (checkout tipo marketplace).

    El carrito puede llevar productos de varias empresas. Se genera UNA
    venta por cada empresa vendedora, todas dentro de una misma transaccion.

    Flujo:
    1. Valida stock de cada item con select_for_update.
    2. Si stock_insuficiente, rechaza con la lista de productos afectados.
    3. Agrupa los items por empresa vendedora y crea una venta por cada una,
       descontando stock y registrando movimientos (transaction.atomic).
    4. Aplica descuento del cupon solo si pertenece a la empresa vendedora.
    5. Simula pasarela de pago (mock configurable por env).
    6. Limpia el carrito.
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

        mock_habilitado = os.environ.get('PASARELA_MOCK', 'True').lower() == 'true'
        if mock_habilitado:
            pasarelarespuesta = {
                'aprobada': True,
                'transaccion_id': f"MOCK-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'mensaje': 'Pago aprobado (mock)',
            }
        else:
            pasarelarespuesta = {
                'aprobada': False,
                'transaccion_id': None,
                'mensaje': 'Pasarela no configurada',
            }

        if not pasarelarespuesta['aprobada']:
            return Response(
                {"codigo": "PAGO_RECHAZADO",
                 "detalle": pasarelarespuesta['mensaje']},
                status=status.HTTP_402_PAYMENT_REQUIRED)

        # Transaccion unica: bloquea el carrito del comprador (evita doble
        # checkout concurrente), los productos y la fila de cada empresa
        # vendedora (serializa el correlativo de numero_factura).
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

            ventas = []
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

                venta = Venta.objects.create(
                    empresa=empresa,
                    cliente=cliente,
                    vendedor=request.user,
                    subtotal=subtotal,
                    descuento=descuento,
                    total=total,
                    estado='completada',
                    metodo_pago=metodo_pago,
                    notas=(f"Checkout tienda - Transaccion: "
                           f"{pasarelarespuesta['transaccion_id']}"
                           + (f" - Cupon: {cupon.codigo}" if cupon and cupon.empresa_id == empresa_id else '')),
                )

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
                        f"Checkout tienda {venta.numero_factura}")

                ventas.append(venta)

            carrito.items.all().delete()
            carrito.cupon = None
            carrito.save(update_fields=['cupon'])

            ActividadUsuario.registrar(
                request.user, "CHECKOUT_MARKETPLACE",
                f"{len(ventas)} venta(s) - Total ${sum(v.total for v in ventas)}")

        return Response({
            "codigo": "EXITO",
            "detalle": "Compra realizada exitosamente.",
            "ventas": [{
                "venta_id": str(v.id),
                "numero_factura": v.numero_factura,
                "empresa_id": str(v.empresa_id),
                "empresa_nombre": v.empresa.nombre,
                "total": str(v.total),
            } for v in ventas],
            "total": str(sum(v.total for v in ventas)),
            "transaccion_id": pasarelarespuesta['transaccion_id'],
        }, status=status.HTTP_201_CREATED)


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
                   .select_related('empresa')
                   .prefetch_related('detalles__producto')
                   .order_by('-created_at'))
        # Lista acotada (nunca ilimitada).
        limite = _limite_paginacion(request.query_params.get('limite', 50))
        datos = PedidoCompradorSerializer(pedidos[:limite], many=True).data
        return Response({"resultados": datos, "total": len(datos)})
