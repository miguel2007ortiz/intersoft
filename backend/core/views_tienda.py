"""API de la fase 5: tienda virtual, carrito y checkout.

Reglas clave:
- Catálogo público: sin autenticación, productos activos agrupados por categoría.
- Carrito: CRUD con validación de stock al agregar/actualizar.
- Cupones: solo vigentes (activo=True, fecha_inicio <= now <= fecha_fin).
- Checkout: reutiliza lógica ACID de VentaPOSView (transaction.atomic + select_for_update).
- Pasarela de pago: mock configurable por variable de entorno (PASARELA_MOCK=True)."""

from decimal import Decimal
import os

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
                                  ProductoTiendaSerializer)


def _obtener_empresa(request):
    return request.user.perfil.empresa


def _empresa_para_catalogo(request, slug=None):
    """Resuelve la empresa del catalogo publico.

    - Si se recibe un slug: se usa esa empresa (para la tienda publica por slug).
    - Si no, y hay sesion: se usa la empresa del usuario autenticado.
    - Si no hay ni slug ni sesion: None (no se filtra por tenant).
    """
    if slug:
        return Empresa.objects.filter(slug=slug).first()
    if getattr(request.user, "is_authenticated", False):
        return request.user.perfil.empresa
    return None


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

    def get(self, request, slug=None):
        empresa = _empresa_para_catalogo(request, slug)
        if slug and empresa is None:
            return Response(
                {"codigo": "TIENDA_NO_ENCONTRADA",
                 "detalle": "La tienda no existe."},
                status=status.HTTP_404_NOT_FOUND)
        if empresa is None:
            return Response({"resultados": [], "total": 0, "categorias": []})

        productos = Producto.objects.filter(
            empresa=empresa, activo=True, deleted_at__isnull=True
        ).select_related('categoria')

        busqueda = request.query_params.get('busqueda', '').strip()
        if busqueda:
            productos = productos.filter(
                Q(nombre__icontains=busqueda)
                | Q(sku__icontains=busqueda)
                | Q(descripcion__icontains=busqueda))

        categoria_id = request.query_params.get('categoria')
        if categoria_id:
            productos = productos.filter(categoria__id=categoria_id)

        precio_min = request.query_params.get('precio_min')
        if precio_min:
            productos = productos.filter(precio__gte=precio_min)

        precio_max = request.query_params.get('precio_max')
        if precio_max:
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

        contexto = {"anonimo": not request.user.is_authenticated}
        serializer = ProductoTiendaSerializer(productos[:50], many=True,
                                              context=contexto)

        categorias = Categoria.objects.filter(empresa=empresa).annotate(
            num_productos=Count('productos', filter=Q(
                productos__activo=True, productos__deleted_at__isnull=True))
        ).filter(num_productos__gt=0).order_by('nombre')

        return Response({
            "resultados": serializer.data,
            "total": len(serializer.data),
            "categorias": CategoriaTiendaSerializer(categorias, many=True).data,
        })


class CatalogoProductoDetailView(APIView):
    """GET detalle de un producto público."""
    permission_classes = [AllowAny]

    def get(self, request, id, slug=None):
        empresa = _empresa_para_catalogo(request, slug)
        if slug and empresa is None:
            return Response(
                {"codigo": "TIENDA_NO_ENCONTRADA",
                 "detalle": "La tienda no existe."},
                status=status.HTTP_404_NOT_FOUND)
        qs = Producto.objects.filter(
            activo=True, deleted_at__isnull=True, id=id
        ).select_related('categoria')
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        producto = qs.first()
        if not producto:
            return Response(
                {"codigo": "NO_ENCONTRADO",
                 "detalle": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND)
        contexto = {"anonimo": not request.user.is_authenticated}
        return Response(ProductoTiendaSerializer(producto, context=contexto).data)


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
    """POST valida un cupón (lo retorna si es vigente)."""
    permission_classes = [AllowAny]

    def post(self, request):
        entrada = CuponValidarSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Debes enviar un codigo.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        codigo = entrada.validated_data['codigo'].upper()
        cupon = Cupon.objects.filter(codigo=codigo).first()

        if not cupon:
            return Response(
                {"codigo": "NO_ENCONTRADO",
                 "detalle": "No existe un cupon con ese codigo."},
                status=status.HTTP_404_NOT_FOUND)

        if not cupon.esta_vigente:
            return Response(
                {"codigo": "CUPON_VENCIDO",
                 "detalle": "Este cupon no esta vigente o ya expiro."},
                status=status.HTTP_400_BAD_REQUEST)

        return Response(CuponSerializer(cupon).data)


# ------------------------------ Carrito ----------------------------------

class CarritoView(APIView):
    """GET retorna el carrito del usuario autenticado."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        carrito, _ = Carrito.objects.get_or_create(
            usuario=request.user,
            empresa=request.user.perfil.empresa
        )
        return Response(CarritoSerializer(carrito).data)


class CarritoItemView(APIView):
    """POST agrega un item / PUT actualiza cantidad / DELETE elimina item."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        entrada = CarritoItemInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos del item.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        empresa = request.user.perfil.empresa
        producto = Producto.objects.filter(
            empresa=empresa, activo=True, deleted_at__isnull=True,
            id=entrada.validated_data['producto']
        ).first()
        if not producto:
            return Response(
                {"codigo": "PRODUCTO_NO_ENCONTRADO",
                 "detalle": "El producto no existe o no esta activo."},
                status=status.HTTP_400_BAD_REQUEST)

        cantidad = entrada.validated_data['cantidad']

        carrito, _ = Carrito.objects.get_or_create(
            usuario=request.user, empresa=empresa)

        item, created = CarritoItem.objects.get_or_create(
            carrito=carrito, producto=producto,
            defaults={'cantidad': cantidad})

        if not created:
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

        return Response(CarritoSerializer(carrito).data,
                        status=status.HTTP_201_CREATED)

    def put(self, request, item_id):
        entrada = CarritoItemInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        empresa = request.user.perfil.empresa
        carrito = Carrito.objects.filter(
            usuario=request.user, empresa=empresa).first()
        if not carrito:
            return Response(
                {"codigo": "CARRITO_VACIO",
                 "detalle": "No tienes un carrito activo."},
                status=status.HTTP_400_BAD_REQUEST)

        item = CarritoItem.objects.filter(
            id=item_id, carrito=carrito).first()
        if not item:
            return Response(
                {"codigo": "ITEM_NO_ENCONTRADO",
                 "detalle": "El item no existe en tu carrito."},
                status=status.HTTP_404_NOT_FOUND)

        nueva_cantidad = entrada.validated_data['cantidad']
        if nueva_cantidad > item.producto.stock:
            return Response(
                {"codigo": "STOCK_INSUFICIENTE",
                 "detalle": f"Stock disponible: {item.producto.stock}."},
                status=status.HTTP_400_BAD_REQUEST)

        item.cantidad = nueva_cantidad
        item.save(update_fields=['cantidad'])

        return Response(CarritoSerializer(carrito).data)

    def delete(self, request, item_id):
        empresa = request.user.perfil.empresa
        carrito = Carrito.objects.filter(
            usuario=request.user, empresa=empresa).first()
        if not carrito:
            return Response(status=status.HTTP_404_NOT_FOUND)

        item = CarritoItem.objects.filter(
            id=item_id, carrito=carrito).first()
        if not item:
            return Response(
                {"codigo": "ITEM_NO_ENCONTRADO",
                 "detalle": "El item no existe en tu carrito."},
                status=status.HTTP_404_NOT_FOUND)

        item.delete()
        return Response(CarritoSerializer(carrito).data)


class CarritoCuponView(APIView):
    """POST aplica un cupón al carrito / DELETE lo quita."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        entrada = CarritoCuponSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Envia el ID del cupon.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        empresa = request.user.perfil.empresa
        carrito, _ = Carrito.objects.get_or_create(
            usuario=request.user, empresa=empresa)

        cupon_id = entrada.validated_data.get('cupon_id')
        if not cupon_id:
            carrito.cupon = None
            carrito.save(update_fields=['cupon'])
            return Response(CarritoSerializer(carrito).data)

        cupon = Cupon.objects.filter(
            id=cupon_id, empresa=empresa).first()
        if not cupon:
            return Response(
                {"codigo": "CUPON_NO_ENCONTRADO",
                 "detalle": "El cupon no existe."},
                status=status.HTTP_404_NOT_FOUND)

        if not cupon.esta_vigente:
            return Response(
                {"codigo": "CUPON_VENCIDO",
                 "detalle": "Este cupon no esta vigente."},
                status=status.HTTP_400_BAD_REQUEST)

        carrito.cupon = cupon
        carrito.save(update_fields=['cupon'])

        return Response(CarritoSerializer(carrito).data)

    def delete(self, request):
        empresa = request.user.perfil.empresa
        carrito = Carrito.objects.filter(
            usuario=request.user, empresa=empresa).first()
        if carrito:
            carrito.cupon = None
            carrito.save(update_fields=['cupon'])
        return Response(CarritoSerializer(carrito).data if carrito else {})


# ------------------------------ Checkout ---------------------------------

class CheckoutView(APIView):
    """POST convierte el carrito en una venta (checkout completo).

    Flujo:
    1. Valida stock de cada item con select_for_update.
    2. Si stock_insuficiente, rechaza con la lista de productos afectados.
    3. Crea venta + detalle + descuenta stock + registra movimientos
       todo dentro de transaction.atomic().
    4. Aplica descuento del cupon si existe.
    5. Simula pasarela de pago (mock configurable por env).
    6. Limpia el carrito.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        empresa = request.user.perfil.empresa

        carrito = Carrito.objects.filter(
            usuario=request.user, empresa=empresa).first()
        if not carrito or not carrito.items.exists():
            return Response(
                {"codigo": "CARRITO_VACIO",
                 "detalle": "Tu carrito esta vacio."},
                status=status.HTTP_400_BAD_REQUEST)

        cliente = Cliente.objects.filter(
            empresa=empresa, deleted_at__isnull=True
        ).first()
        if not cliente:
            return Response(
                {"codigo": "SIN_CLIENTE",
                 "detalle": "No hay clientes registrados. "
                            "Crea un cliente primero."},
                status=status.HTTP_400_BAD_REQUEST)

        items = carrito.items.select_related('producto').all()

        # Transaccion unica: el lock sobre la empresa serializa el consecutivo
        # de la factura y el descuento de stock para este tenant.
        with transaction.atomic():
            Empresa.objects.select_for_update().filter(pk=empresa.pk).get()

            lineas_stock_ok = []
            lineas_stock_fallido = []
            for item in items:
                producto = Producto.objects.select_for_update().filter(
                    empresa=empresa, deleted_at__isnull=True,
                    id=item.producto.id
                ).first()
                if not producto:
                    lineas_stock_fallido.append({
                        'producto': str(item.producto.id),
                        'producto_nombre': 'No encontrado',
                        'solicitado': item.cantidad,
                        'disponible': 0,
                    })
                    continue
                if producto.stock < item.cantidad:
                    lineas_stock_fallido.append({
                        'producto': str(producto.id),
                        'producto_nombre': producto.nombre,
                        'solicitado': item.cantidad,
                        'disponible': producto.stock,
                    })
                    continue
                lineas_stock_ok.append({
                    'producto': producto,
                    'cantidad': item.cantidad,
                    'precio_unitario': producto.precio,
                })

            if lineas_stock_fallido:
                return Response(
                    {"codigo": "STOCK_INSUFICIENTE",
                     "detalle": "Algunos productos no tienen stock suficiente.",
                     "productos": lineas_stock_fallido},
                    status=status.HTTP_400_BAD_REQUEST)

            subtotal = sum(
                Decimal(str(l['precio_unitario'])) * l['cantidad']
                for l in lineas_stock_ok
            )

            descuento = Decimal('0')
            cupon = carrito.cupon
            if cupon and cupon.esta_vigente:
                descuento = subtotal * cupon.porcentaje / Decimal('100')

            total = max(subtotal - descuento, Decimal('0'))

            metodo_pago = request.data.get('metodo_pago', 'tarjeta')

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

            venta = Venta.objects.create(
                empresa=empresa,
                cliente=cliente,
                vendedor=request.user,
                subtotal=subtotal,
                descuento=descuento,
                total=total,
                estado='completada',
                metodo_pago=metodo_pago,
                notas=f"Checkout tienda - Transaccion: {pasarelarespuesta['transaccion_id']}"
                      + (f" - Cupon: {cupon.codigo}" if cupon else ''),
            )

            for linea in lineas_stock_ok:
                producto = linea['producto']
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=linea['cantidad'],
                    precio_unitario=linea['precio_unitario'],
                )
                actualizado = Producto.objects.filter(
                    pk=producto.pk, empresa=empresa,
                    deleted_at__isnull=True, stock__gte=linea['cantidad'],
                ).update(stock=models.F('stock') - linea['cantidad'])
                if not actualizado:
                    transaction.set_rollback(True)
                    return Response(
                        {"codigo": "STOCK_INSUFICIENTE",
                         "detalle": "El stock del producto cambio durante el checkout.",
                         "productos": [{
                             'producto': str(producto.id),
                             'producto_nombre': producto.nombre,
                             'solicitado': linea['cantidad'],
                             'disponible': producto.stock,
                         }]},
                        status=status.HTTP_400_BAD_REQUEST)
                producto.stock = max(producto.stock - linea['cantidad'], 0)
                _registrar_movimiento(
                    producto, request.user, 'salida', linea['cantidad'],
                    f"Checkout tienda {venta.numero_factura}")

            ActividadUsuario.registrar(
                request.user, "CHECKOUT_COMPLETADO",
                f"Factura {venta.numero_factura} - Total ${total} "
                + (f"- Cupon {cupon.codigo}" if cupon else ''))

            items.delete()

        return Response({
            "codigo": "EXITO",
            "detalle": "Compra realizada exitosamente.",
            "venta_id": str(venta.id),
            "numero_factura": venta.numero_factura,
            "total": str(venta.total),
            "transaccion_id": pasarelarespuesta['transaccion_id'],
        }, status=status.HTTP_201_CREATED)
