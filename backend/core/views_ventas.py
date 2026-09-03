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

import re
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsPersonal

from .models import (Cliente, DetalleVenta, Empresa, Envio,
                     MovimientoInventario, Notificacion, Producto, Venta)
from .serializers_monitoreo import NotificacionLecturaSerializer
from .serializers_ventas import (AjusteInventarioSerializer,
                                 AlertaReabastecerSerializer, AnulacionSerializer,
                                 EnvioEstadoInputSerializer, EnvioLecturaSerializer,
                                 MovimientoInventarioLecturaSerializer,
                                 VentaLecturaSerializer, VentaPOSInputSerializer)


def _obtener_empresa(request):
    return request.user.perfil.empresa


def _es_fecha_valida(valor):
    """True si `valor` es una fecha ISO YYYY-MM-DD real (p. ej. '2026-09-01')."""
    try:
        timezone.datetime.strptime(valor, '%Y-%m-%d')
    except (TypeError, ValueError):
        return False
    return True


def _limite_paginacion(valor, por_defecto=50, maximo=200):
    """Limite de filas a devolver: acotado a [1, maximo] para que una
    lista nunca devuelva resultados ilimitados (uso de memoria/CPU acotado)."""
    try:
        return max(1, min(int(valor), maximo))
    except (TypeError, ValueError):
        return por_defecto


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

        # Un solo bloque transaction.atomic(): valida stock con
        # select_for_update, crea la venta, descuenta stock y registra
        # movimientos manteniendo el lock de producto hasta el commit
        # (evita oversell entre dos POST simultaneos).
        lineas_stock_ok = []
        lineas_stock_fallido = []
        with transaction.atomic():
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

            # Lock de la fila de la empresa: serializa el correlativo
            # numero_factura dentro de la misma empresa.
            Empresa.objects.select_for_update().filter(pk=empresa.pk).first()

            subtotal = sum(
                Decimal(str(linea['precio_unitario'])) * linea['cantidad']
                for linea in lineas_stock_ok
            )
            descuento = Decimal(str(datos['descuento']))
            if descuento > subtotal:
                return Response(
                    {"codigo": "DESCUENTO_INVALIDO",
                     "detalle": f"El descuento (${descuento}) no puede superar "
                                f"el subtotal (${subtotal})."},
                    status=status.HTTP_400_BAD_REQUEST)
            total = subtotal - descuento

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
                # Descontar stock
                producto.stock -= linea['cantidad']
                producto.save(update_fields=['stock'])
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
        if not request.user.perfil.tiene_permiso("venta.leer_todas"):
            # RN Empleados: sin permiso global, cada quien ve solo lo suyo.
            ventas = ventas.filter(vendedor=request.user)

        # Filtros
        estado = request.query_params.get('estado')
        if estado:
            ventas = ventas.filter(estado=estado)

        fecha_inicio = request.query_params.get('fecha_inicio')
        if fecha_inicio and not _es_fecha_valida(fecha_inicio):
            return Response(
                {"codigo": "FECHA_INVALIDA",
                 "detalle": "fecha_inicio debe usar el formato YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST)
        if fecha_inicio:
            ventas = ventas.filter(fecha__date__gte=fecha_inicio)

        fecha_fin = request.query_params.get('fecha_fin')
        if fecha_fin and not _es_fecha_valida(fecha_fin):
            return Response(
                {"codigo": "FECHA_INVALIDA",
                 "detalle": "fecha_fin debe usar el formato YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST)
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
            total_count=Count('id'),
        )

        datos = VentaLecturaSerializer(
            ventas.order_by('-fecha')[:50].prefetch_related('detalles__producto'),
            many=True).data

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
        # Valida el motivo antes de tomar lock (evita sostener filas
        # bloqueadas por una peticion malformada).
        entrada = AnulacionSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Debes indicar el motivo de anulacion.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        # Dentro del bloque transaction.atomic() se toma el lock de la fila
        # de la venta (serializa dobles anulaciones) y el de los productos.
        with transaction.atomic():
            venta = Venta.objects.select_for_update().filter(
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

            # Lock de las filas de producto para revertir stock sin
            # colisionar con ventas POS o ajustes concurrentes.
            detalles = list(venta.detalles.select_related('producto').all())
            Producto.objects.filter(
                id__in=[d.producto_id for d in detalles],
                empresa=empresa,
            ).select_for_update().all()

            # Revertir stock con la fila ya bloqueada
            for detalle in detalles:
                producto = detalle.producto
                producto.stock += detalle.cantidad
                producto.save(update_fields=['stock'])
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


# ------------------------------ Envios (fase 10) ---------------------------

class EnviosView(APIView):
    """GET lista los envios de la empresa (personal interno), opcionalmente
    filtrada por estado. Ordenada por antiguedad (los mas viejos primero):
    es una cola de trabajo, no un historial."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        empresa = _obtener_empresa(request)
        envios = Envio.objects.select_related('venta', 'venta__cliente').filter(
            venta__empresa=empresa)

        estado = request.query_params.get('estado')
        if estado:
            if estado not in dict(Envio.ESTADO_CHOICES):
                return Response(
                    {"codigo": "ESTADO_INVALIDO",
                     "detalle": "Estado de envio no valido.",
                     "opciones": [c for c, _ in Envio.ESTADO_CHOICES]},
                    status=status.HTTP_400_BAD_REQUEST)
            envios = envios.filter(estado=estado)

        envios = envios.order_by('created_at')
        limite = _limite_paginacion(request.query_params.get('limite', 50))
        datos = EnvioLecturaSerializer(envios[:limite], many=True).data
        return Response({"resultados": datos, "total": len(datos)})


class EnvioDetalleView(APIView):
    """GET detalle del envio de una venta / PATCH actualiza transportadora,
    numero de guia, notas y/o estado (con validacion de transicion)."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request, id):
        empresa = _obtener_empresa(request)
        envio = Envio.objects.select_related('venta').filter(
            venta__empresa=empresa, venta_id=id).first()
        if not envio:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(EnvioLecturaSerializer(envio).data)

    def patch(self, request, id):
        empresa = _obtener_empresa(request)
        entrada = EnvioEstadoInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS", "detalle": "Revisa los datos del envio.",
                 "errores": entrada.errors}, status=status.HTTP_400_BAD_REQUEST)
        datos = entrada.validated_data

        # select_for_update: serializa cambios de estado concurrentes sobre
        # el mismo envio (mismo criterio que anular venta / ajustar stock).
        with transaction.atomic():
            envio = Envio.objects.select_for_update().select_related('venta').filter(
                venta__empresa=empresa, venta_id=id).first()
            if not envio:
                return Response(status=status.HTTP_404_NOT_FOUND)

            campos_planos = [c for c in
                             ('transportadora', 'numero_guia', 'fecha_entrega_estimada', 'notas')
                             if c in datos]
            for campo in campos_planos:
                setattr(envio, campo, datos[campo])
            if campos_planos:
                envio.save(update_fields=campos_planos + ['updated_at'])

            nuevo_estado = datos.get('estado')
            if nuevo_estado:
                try:
                    envio.cambiar_estado(nuevo_estado)
                except Envio.TransicionInvalida as exc:
                    return Response(
                        {"codigo": "TRANSICION_INVALIDA", "detalle": str(exc)},
                        status=status.HTTP_400_BAD_REQUEST)

            ActividadUsuario.registrar(
                request.user, "ENVIO_ACTUALIZADO",
                f"Envio de {envio.venta.numero_factura} -> {envio.get_estado_display()}")

        return Response(EnvioLecturaSerializer(envio).data)


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

    def post(self, request, id=None):
        return self.ajuste_manual(request, id=id)

    def ajuste_manual(self, request, id=None):
        # La ruta /inventario/<uuid:id>/ajustar/ identifica el producto por
        # URL; en ese caso `producto` no se exige en el cuerpo. En el POST
        # canonico /inventario/ (usado por el frontend) viene en el payload.
        datos = request.data.copy() if hasattr(request.data, "copy") \
            else dict(request.data)
        if id is not None:
            datos["producto"] = id
        entrada = AjusteInventarioSerializer(data=datos)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos del ajuste.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        datos = entrada.validated_data
        empresa = _obtener_empresa(request)

        with transaction.atomic():
            # Lock dentro de la transaccion: el stock se lee y escribe bajo
            # SELECT FOR UPDATE.
            producto = Producto.objects.select_for_update().filter(
                empresa=empresa, deleted_at__isnull=True, id=datos['producto']
            ).first()
            if not producto:
                return Response(
                    {"codigo": "PRODUCTO_NO_ENCONTRADO",
                     "detalle": "El producto no existe en tu empresa."},
                    status=status.HTTP_400_BAD_REQUEST)

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

        movimiento = (MovimientoInventario.objects
                      .filter(producto__empresa=empresa)
                      .latest('created_at'))
        return Response(MovimientoInventarioLecturaSerializer(movimiento).data,
                        status=status.HTTP_201_CREATED)


# ------------------------------ Alertas -----------------------------------

class AlertasView(APIView):
    """GET lista alertas de stock / POST marca como revisada."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        alertas = Notificacion.objects.filter(
            empresa=_obtener_empresa(request), leida=False)
        datos = NotificacionLecturaSerializer(
            alertas.order_by('-created_at')[:50], many=True).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request, id):
        alerta = Notificacion.objects.filter(
            empresa=_obtener_empresa(request), id=id).first()
        if not alerta:
            return Response(status=status.HTTP_404_NOT_FOUND)

        alerta.leida = True
        alerta.save(update_fields=['leida'])

        ActividadUsuario.registrar(
            request.user, "ALERTA_REVISADA",
            f"Alerta #{str(alerta.id)[:8]} marcada como resuelta")

        return Response(NotificacionLecturaSerializer(alerta).data)


class AlertaActualizarStockView(APIView):
    """POST reabastece el producto de una alerta de stock bajo: aumenta el
    stock, registra el movimiento de inventario y marca la alerta como
    revisada, todo en una sola transaccion.

    Body opcional `{"cantidad": N}`; sin ella, repone lo necesario para
    superar el minimo (stock_minimo - stock + 1)."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request, id):
        empresa = _obtener_empresa(request)
        alerta = Notificacion.objects.filter(empresa=empresa, id=id).first()
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
        match = re.search(r'\(([^)]+)\)', mensaje)
        if not match:
            return Response(
                {"codigo": "ALERTA_INVALIDA",
                 "detalle": "No se pudo identificar el producto."},
                status=status.HTTP_400_BAD_REQUEST)
        sku = match.group(1)

        entrada = AlertaReabastecerSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "La cantidad debe ser un entero mayor a 0.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            producto = Producto.objects.select_for_update().filter(
                empresa=empresa, sku=sku, deleted_at__isnull=True).first()
            if not producto:
                return Response(
                    {"codigo": "PRODUCTO_NO_ENCONTRADO",
                     "detalle": "El producto ya no existe."},
                    status=status.HTTP_400_BAD_REQUEST)

            cantidad = entrada.validated_data.get('cantidad') or max(
                producto.stock_minimo - producto.stock + 1, 1)

            producto.stock += cantidad
            producto.save(update_fields=['stock'])
            _registrar_movimiento(
                producto, request.user, 'entrada', cantidad,
                f"Reabastecimiento desde alerta #{str(alerta.id)[:8]}")

            alerta.leida = True
            alerta.save(update_fields=['leida'])

            ActividadUsuario.registrar(
                request.user, "ALERTA_REABASTECIDA",
                f"{producto.nombre}: +{cantidad} unidades "
                f"(alerta #{str(alerta.id)[:8]})")

        return Response({
            "producto": {
                "id": str(producto.id),
                "nombre": producto.nombre,
                "sku": producto.sku,
                "stock": producto.stock,
                "stock_minimo": producto.stock_minimo,
            },
            "cantidad_agregada": cantidad,
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

        # Lista acotada (nunca ilimitada).
        limite = _limite_paginacion(
            request.query_params.get('limite', 50))
        datos = []
        for p in productos[:limite]:
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
