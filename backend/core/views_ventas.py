"""API de la fase 4: ventas POS, inventario y alertas (personal interno).

Reglas clave:
- Crear venta: transaction.atomic() con SELECT_FOR_UPDATE para evitar
  carreras de stock; si stock_insuficiente en alguna linea, se rechaza
  esa linea y se pide ajustar cantidad (sin venta parcial).
- Anular venta: solo antes del cierre de caja (si la venta ya fue
  facturada ante la DIAN, se exige Nota Credito — pendiente fase 6);
  revierte el stock y registra el motivo.
- Cada movimiento de inventario inserta movimiento_inventario y evalua
  si stock <= stock_minimo para insertar notificacion de alerta.
- Productos desactivados no generan alerta aunque tengan stock bajo.
- Todo queda auditado en actividad_usuario."""

from decimal import Decimal

from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsPersonal

from .models import (Cliente, DetalleVenta, Empresa, MovimientoInventario,
                     Notificacion, Producto, Venta)
from .serializers_monitoreo import NotificacionLecturaSerializer
from .serializers_ventas import (AjusteInventarioSerializer, AnulacionSerializer,
                                 MovimientoInventarioLecturaSerializer,
                                 VentaLecturaSerializer, VentaPOSInputSerializer)


def _obtener_empresa(request):
    return request.user.perfil.empresa


def _registrar_alerta_stock(producto, empresa):
    """Inserta notificacion si stock <= stock_minimo y el producto esta activo."""
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
    """Registra un movimiento de inventario y evalua alerta de stock."""
    MovimientoInventario.objects.create(
        producto=producto, usuario=usuario, tipo=tipo,
        cantidad=cantidad, motivo=motivo,
    )
    _registrar_alerta_stock(producto, producto.empresa)


# ------------------------------ POS (Crear venta) -------------------------

class VentaPOSView(APIView):
    """POST crea una venta desde el POS con logica ACID.

    Flujo:
    1. Valida stock por linea con select_for_update.
    2. Si stock_insuficiente en alguna linea, rechaza con la lista
       de productos sin stock.
    3. Crea venta + detalle + descuenta stock + registra movimientos
       todo dentro de transaction.atomic().
    4. Total = (suma de detalle) - descuento.
    """
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request):
        entrada = VentaPOSInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos de la venta.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        datos = entrada.validated_data
        empresa = _obtener_empresa(request)

        # Obtener cliente
        cliente = Cliente.objects.filter(
            empresa=empresa, deleted_at__isnull=True, id=datos['cliente']
        ).first()
        if not cliente:
            return Response(
                {"codigo": "CLIENTE_NO_ENCONTRADO",
                 "detalle": "El cliente no existe en tu empresa."},
                status=status.HTTP_400_BAD_REQUEST)

        # Transaccion unica: lock de empresa + validacion de stock + creacion.
        # El SELECT FOR UPDATE sobre la empresa serializa el consecutivo y el
        # descuento de stock para esa empresa (evita carreras y negativos).
        with transaction.atomic():
            Empresa.objects.select_for_update().filter(pk=empresa.pk).get()

            lineas_stock_ok = []
            lineas_stock_fallido = []
            for linea in datos['detalles']:
                producto = Producto.objects.select_for_update().filter(
                    empresa=empresa, deleted_at__isnull=True, id=linea['producto']
                ).first()
                if not producto:
                    lineas_stock_fallido.append({
                        'producto': str(linea['producto']),
                        'producto_nombre': 'No encontrado',
                        'solicitado': linea['cantidad'],
                        'disponible': 0,
                    })
                    continue
                if producto.stock < linea['cantidad']:
                    lineas_stock_fallido.append({
                        'producto': str(producto.id),
                        'producto_nombre': producto.nombre,
                        'solicitado': linea['cantidad'],
                        'disponible': producto.stock,
                    })
                    continue
                lineas_stock_ok.append({
                    'producto': producto,
                    'cantidad': linea['cantidad'],
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
            descuento = Decimal(str(datos['descuento']))
            total = max(subtotal - descuento, Decimal('0'))

            venta = Venta.objects.create(
                empresa=empresa,
                cliente=cliente,
                vendedor=request.user,
                subtotal=subtotal,
                descuento=descuento,
                total=total,
                estado='completada',
                metodo_pago=datos['metodo_pago'],
                notas=datos.get('notas', ''),
            )

            for linea in lineas_stock_ok:
                producto = linea['producto']
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=linea['cantidad'],
                    precio_unitario=linea['precio_unitario'],
                )
                # Descuento atomico de stock (no puede quedar negativo).
                #
                # Bajado con F() contra el numero activo con cantidad
                # garantizando stock >= cantidad.
                actualizado = Producto.objects.filter(
                    pk=producto.pk, empresa=empresa,
                    deleted_at__isnull=True, stock__gte=linea['cantidad'],
                ).update(stock=models.F('stock') - linea['cantidad'])
                if not actualizado:
                    transaction.set_rollback(True)
                    return Response(
                        {"codigo": "STOCK_INSUFICIENTE",
                         "detalle": "El stock del producto cambio durante la venta.",
                         "productos": [{
                             'producto': str(producto.id),
                             'producto_nombre': producto.nombre,
                             'solicitado': linea['cantidad'],
                             'disponible': producto.stock,
                         }]},
                        status=status.HTTP_400_BAD_REQUEST)
                producto.stock = max(producto.stock - linea['cantidad'], 0)
                # Registrar movimiento
                _registrar_movimiento(
                    producto, request.user, 'salida', linea['cantidad'],
                    f"Venta {venta.numero_factura}")

            ActividadUsuario.registrar(
                request.user, "VENTA_CREADA",
                f"Factura {venta.numero_factura} - "
                f"{cliente.nombre} (${total})")

        return Response(VentaLecturaSerializer(venta).data,
                        status=status.HTTP_201_CREATED)


# ------------------------------ Listar ventas -----------------------------

class VentasView(APIView):
    """GET lista ventas con filtros opcionales."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        empresa = _obtener_empresa(request)
        ventas = Venta.objects.select_related('cliente', 'vendedor').filter(
            empresa=empresa, deleted_at__isnull=True)

        # Filtros
        estado = request.query_params.get('estado')
        if estado:
            ventas = ventas.filter(estado=estado)

        fecha_inicio = request.query_params.get('fecha_inicio')
        if fecha_inicio:
            ventas = ventas.filter(fecha__date__gte=fecha_inicio)

        fecha_fin = request.query_params.get('fecha_fin')
        if fecha_fin:
            ventas = ventas.filter(fecha__date__lte=fecha_fin)

        busqueda = request.query_params.get('busqueda', '').strip()
        if busqueda:
            ventas = ventas.filter(
                Q(numero_factura__icontains=busqueda)
                | Q(cliente__nombre__icontains=busqueda))

        # Estadisticas
        stats = ventas.aggregate(
            total_ventas=Sum('total'),
            total_count=Sum('id'),
        )

        datos = VentaLecturaSerializer(
            ventas.order_by('-fecha')[:50], many=True).data

        return Response({
            "resultados": datos,
            "total": len(datos),
            "estadisticas": {
                "total_ventas": str(stats['total_ventas'] or 0),
                "total_registros": stats['total_count'] or 0,
            }
        })


class VentaDetalleView(APIView):
    """GET detalle de una venta / POST anular venta."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request, id):
        empresa = _obtener_empresa(request)
        venta = Venta.objects.select_related('cliente', 'vendedor').prefetch_related(
            'detalles__producto').filter(
            empresa=empresa, deleted_at__isnull=True, id=id).first()
        if not venta:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(VentaLecturaSerializer(venta).data)

    def post(self, request, id):
        return self.anular(request, id)

    def anular(self, request, id):
        empresa = _obtener_empresa(request)
        venta = Venta.objects.filter(
            empresa=empresa, deleted_at__isnull=True, id=id).first()
        if not venta:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if venta.estado == 'anulada':
            return Response(
                {"codigo": "YA_ANULADA",
                 "detalle": "Esta venta ya fue anulada."},
                status=status.HTTP_400_BAD_REQUEST)

        if venta.estado != 'completada':
            return Response(
                {"codigo": "ESTADO_INVALIDO",
                 "detalle": "Solo se pueden anular ventas completadas."},
                status=status.HTTP_400_BAD_REQUEST)

        if hasattr(venta, 'factura_electronica') and \
                venta.factura_electronica.estado == 'aprobada':
            return Response(
                {"codigo": "FACTURADA_DIAN",
                 "detalle": "Esta venta ya fue facturada ante la DIAN. "
                            "Para reversarla, crea una Nota Credito desde "
                            "el modulo de Facturacion."},
                status=status.HTTP_400_BAD_REQUEST)

        entrada = AnulacionSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Debes indicar el motivo de anulacion.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Revertir stock (incremento atomico para evitar perdidas)
            detalles = venta.detalles.select_related('producto').all()
            for detalle in detalles:
                producto = detalle.producto
                Producto.objects.filter(
                    pk=producto.pk, empresa=empresa,
                ).update(stock=models.F('stock') + detalle.cantidad)
                producto.stock += detalle.cantidad
                _registrar_movimiento(
                    producto, request.user, 'entrada', detalle.cantidad,
                    f"Anulacion venta {venta.numero_factura}")

            venta.estado = 'anulada'
            venta.motivo_anulacion = entrada.validated_data['motivo']
            venta.anulada_en = timezone.now()
            venta.save(update_fields=['estado', 'motivo_anulacion', 'anulada_en'])

            ActividadUsuario.registrar(
                request.user, "VENTA_ANULADA",
                f"Factura {venta.numero_factura} - "
                f"Motivo: {venta.motivo_anulacion}")

        return Response(VentaLecturaSerializer(venta).data)


# ------------------------------ Inventario --------------------------------

class InventarioView(APIView):
    """GET lista movimientos de inventario / POST ajuste manual."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        empresa = _obtener_empresa(request)
        movimientos = MovimientoInventario.objects.select_related(
            'producto', 'usuario').filter(
            producto__empresa=empresa)

        # Filtros
        producto_id = request.query_params.get('producto')
        if producto_id:
            movimientos = movimientos.filter(producto__id=producto_id)

        tipo = request.query_params.get('tipo')
        if tipo:
            movimientos = movimientos.filter(tipo=tipo)

        datos = MovimientoInventarioLecturaSerializer(
            movimientos.order_by('-created_at')[:100], many=True).data

        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request):
        return self.ajuste_manual(request)

    def ajuste_manual(self, request):
        entrada = AjusteInventarioSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos del ajuste.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        datos = entrada.validated_data
        empresa = _obtener_empresa(request)

        producto = Producto.objects.select_for_update().filter(
            empresa=empresa, deleted_at__isnull=True, id=datos['producto']
        ).first()
        if not producto:
            return Response(
                {"codigo": "PRODUCTO_NO_ENCONTRADO",
                 "detalle": "El producto no existe en tu empresa."},
                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            tipo = datos['tipo']
            cantidad = datos['cantidad']
            motivo = datos['motivo']

            if tipo == 'salida' and producto.stock < cantidad:
                return Response(
                    {"codigo": "STOCK_INSUFICIENTE",
                     "detalle": f"Stock actual: {producto.stock}, "
                                f"solicitado: {cantidad}."},
                    status=status.HTTP_400_BAD_REQUEST)

            if tipo == 'entrada':
                producto.stock += cantidad
            else:
                producto.stock -= cantidad
            producto.save(update_fields=['stock'])

            _registrar_movimiento(
                producto, request.user, tipo, cantidad, motivo)

            ActividadUsuario.registrar(
                request.user, "AJUSTE_INVENTARIO",
                f"{tipo.upper()} {cantidad} - {producto.nombre}: {motivo}")

        return Response(MovimientoInventarioLecturaSerializer(
            MovimientoInventario.objects.latest('created_at')).data,
            status=status.HTTP_201_CREATED)


# ------------------------------ Alertas -----------------------------------

class AlertasView(APIView):
    """GET lista alertas de stock / POST marca como revisada."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        alertas = Notificacion.objects.filter(
            empresa=request.user.perfil.empresa, leida=False)
        datos = NotificacionLecturaSerializer(
            alertas.order_by('-created_at')[:50], many=True).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request, id):
        alerta = Notificacion.objects.filter(
            empresa=request.user.perfil.empresa, id=id).first()
        if not alerta:
            return Response(status=status.HTTP_404_NOT_FOUND)

        alerta.leida = True
        alerta.save(update_fields=['leida'])

        ActividadUsuario.registrar(
            request.user, "ALERTA_REVISADA",
            f"Alerta #{str(alerta.id)[:8]} marcada como resuelta")

        return Response(NotificacionLecturaSerializer(alerta).data)


class AlertaActualizarStockView(APIView):
    """POST reabastece directamente desde la alerta."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request, id):
        alerta = Notificacion.objects.filter(
            empresa=request.user.perfil.empresa, id=id).first()
        if not alerta:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Extraer el nombre del producto del mensaje de la alerta
        # Formato: "Stock bajo: NOMBRE (SKU) tiene X unidades (minimo Y)."
        mensaje = alerta.mensaje
        if 'Stock bajo:' not in mensaje:
            return Response(
                {"codigo": "ALERTA_INVALIDA",
                 "detalle": "Esta alerta no esta vinculada a un producto."},
                status=status.HTTP_400_BAD_REQUEST)

        # Buscar el producto por SKU en el mensaje
        import re
        match = re.search(r'\(([^)]+)\)', mensaje)
        if not match:
            return Response(
                {"codigo": "ALERTA_INVALIDA",
                 "detalle": "No se pudo identificar el producto."},
                status=status.HTTP_400_BAD_REQUEST)

        sku = match.group(1)
        producto = Producto.objects.filter(
            empresa=request.user.perfil.empresa,
            sku=sku, deleted_at__isnull=True).first()
        if not producto:
            return Response(
                {"codigo": "PRODUCTO_NO_ENCONTRADO",
                 "detalle": "El producto ya no existe."},
                status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "producto": {
                "id": str(producto.id),
                "nombre": producto.nombre,
                "sku": producto.sku,
                "stock": producto.stock,
                "stock_minimo": producto.stock_minimo,
            }
        })


class InventarioProductosView(APIView):
    """GET lista productos con su estado de stock (para panel de inventario)."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        empresa = _obtener_empresa(request)
        productos = Producto.objects.filter(
            empresa=empresa, deleted_at__isnull=True, activo=True
        ).order_by('nombre')

        # Filtros
        busqueda = request.query_params.get('busqueda', '').strip()
        if busqueda:
            productos = productos.filter(
                Q(nombre__icontains=busqueda) | Q(sku__icontains=busqueda))

        filtro_stock = request.query_params.get('stock_bajo')
        if filtro_stock == 'true':
            productos = productos.filter(stock__lte=models.F('stock_minimo'))

        datos = []
        for p in productos:
            datos.append({
                "id": str(p.id),
                "nombre": p.nombre,
                "sku": p.sku,
                "categoria": p.categoria.nombre if p.categoria else None,
                "precio": str(p.precio),
                "stock": p.stock,
                "stock_minimo": p.stock_minimo,
                "stock_bajo": p.stock <= p.stock_minimo,
            })

        return Response({"resultados": datos, "total": len(datos)})
