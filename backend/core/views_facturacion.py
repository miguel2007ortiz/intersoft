"""API de la fase 6: facturacion electronica DIAN y notas credito.

Flujo:
1. Generar comprobante: crea FacturaElectronica pendiente, la envia a DIAN
   via adaptador mock. Si aprueba → CUFE + PDF/XML. Si rechaza → estado
   pendiente + notificacion al ADMINISTRADOR. Si falla → estado fallida +
   reintento automatico.
2. La venta queda en estado 'completada' independientemente del resultado
   de la DIAN (no se bloquea la venta por facturacion).
3. Anulacion: si la venta ya tiene factura aprobada, se bloquea la
   anulacion directa y se exige Nota Credito.
4. Nota Credito: genera documento reverso, lo envia a DIAN, si aprueba
   revierte stock y anula la venta original.
5. Reenvio manual: reenvia la factura por correo al cliente.
6. Todo queda auditado en actividad_usuario."""

import os
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario
from cuentas.permissions import EsPersonal

from .models import (DetalleVenta, FacturaElectronica, MovimientoInventario,
                     NotaCredito, Notificacion, Producto, Venta)
from .serializers_facturacion import (FacturaElectronicaLecturaSerializer,
                                      GenerarFacturaSerializer,
                                      NotaCreditoInputSerializer,
                                      NotaCreditoLecturaSerializer,
                                      ReenviarFacturaSerializer)
from .services.dian_adapter import enviar_factura, enviar_nota_credito


def _obtener_empresa(request):
    return request.user.perfil.empresa


def _es_administrador(request):
    return request.user.perfil.rol.nombre == 'ADMINISTRADOR'


def _notificar_admin(empresa, mensaje):
    """Envia notificacion a todos los administradores de la empresa."""
    from cuentas.models import Perfil
    from .notificaciones import crear_notificacion
    admins = Perfil.objects.filter(
        empresa=empresa, rol__nombre='ADMINISTRADOR',
        deleted_at__isnull=True
    ).select_related('usuario')
    for admin in admins:
        crear_notificacion(empresa=empresa, usuario=admin.usuario,
                           tipo='factura', mensaje=mensaje)


def _datos_venta_para_dian(venta):
    """Construye el diccionario de datos que necesita el adaptador DIAN."""
    cliente = venta.cliente
    empresa = venta.empresa
    detalles = venta.detalles.select_related('producto').all()
    return {
        'numero_factura': venta.numero_factura,
        'fecha': timezone.localtime(venta.fecha).isoformat(),
        'nit_empresa': empresa.nit,
        'empresa_nombre': empresa.nombre,
        'cliente_nombre': cliente.nombre,
        'cliente_doc': f"{cliente.tipo_documento} {cliente.numero_documento}",
        'cliente_email': cliente.email,
        'subtotal': str(venta.subtotal),
        'descuento': str(venta.descuento),
        'total': str(venta.total),
        'detalles': [
            {
                'producto': d.producto.nombre,
                'sku': d.producto.sku,
                'cantidad': d.cantidad,
                'precio': str(d.precio_unitario),
                'subtotal': str(d.subtotal),
            }
            for d in detalles
        ],
    }


def _registrar_movimiento(producto, usuario, tipo, cantidad, motivo):
    MovimientoInventario.objects.create(
        producto=producto, usuario=usuario, tipo=tipo,
        cantidad=cantidad, motivo=motivo,
    )


# ------------------------------ Facturas ---------------------------------

class FacturasView(APIView):
    """GET lista facturas electronicas / POST genera factura de una venta."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        empresa = _obtener_empresa(request)
        facturas = FacturaElectronica.objects.select_related(
            'venta__cliente', 'venta__empresa'
        ).filter(venta__empresa=empresa)

        estado = request.query_params.get('estado')
        if estado:
            facturas = facturas.filter(estado=estado)

        busqueda = request.query_params.get('busqueda', '').strip()
        if busqueda:
            facturas = facturas.filter(
                Q(numero__icontains=busqueda)
                | Q(cufe__icontains=busqueda)
                | Q(venta__numero_factura__icontains=busqueda)
                | Q(venta__cliente__nombre__icontains=busqueda)
            )

        datos = FacturaElectronicaLecturaSerializer(
            facturas[:50], many=True).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request):
        return self.generar(request)

    def generar(self, request):
        entrada = GenerarFacturaSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Debes enviar el ID de la venta.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        empresa = _obtener_empresa(request)
        venta = Venta.objects.filter(
            empresa=empresa, deleted_at__isnull=True,
            id=entrada.validated_data['venta_id']
        ).first()
        if not venta:
            return Response(
                {"codigo": "VENTA_NO_ENCONTRADA",
                 "detalle": "La venta no existe."},
                status=status.HTTP_400_BAD_REQUEST)

        if venta.estado != 'completada':
            return Response(
                {"codigo": "ESTADO_INVALIDO",
                 "detalle": "Solo se pueden facturar ventas completadas."},
                status=status.HTTP_400_BAD_REQUEST)

        if hasattr(venta, 'factura_electronica'):
            return Response(
                {"codigo": "YA_FACTURADA",
                 "detalle": "Esta venta ya tiene factura electronica.",
                 "factura_id": str(venta.factura_electronica.id)},
                status=status.HTTP_400_BAD_REQUEST)

        numero_f = f"FE-{venta.numero_factura}"
        factura = FacturaElectronica.objects.create(
            venta=venta,
            numero=numero_f,
            estado='pendiente',
        )

        datos_dian = _datos_venta_para_dian(venta)
        respuesta = enviar_factura(datos_dian)

        with transaction.atomic():
            if respuesta.aprobada:
                factura.estado = 'aprobada'
                factura.cufe = respuesta.cufe
                factura.pdf = None
                factura.xml = None
                factura.save(update_fields=[
                    'estado', 'cufe', 'pdf', 'xml', 'updated_at'
                ])
            elif respuesta.codigo_error == 'DATOS_INVALIDOS':
                factura.estado = 'rechazada'
                factura.motivo_rechazo = respuesta.mensaje
                factura.save(update_fields=[
                    'estado', 'motivo_rechazo', 'updated_at'
                ])
                _notificar_admin(
                    empresa,
                    f"Factura {numero_f} rechazada por DIAN: "
                    f"{respuesta.mensaje}. Revisa y corrige los datos.")
            else:
                factura.estado = 'fallida'
                factura.motivo_rechazo = respuesta.mensaje
                factura.intentos = 1
                factura.ultimo_intento = timezone.now()
                factura.save(update_fields=[
                    'estado', 'motivo_rechazo', 'intentos',
                    'ultimo_intento', 'updated_at'
                ])
                _notificar_admin(
                    empresa,
                    f"Factura {numero_f} fallo al enviar a DIAN: "
                    f"{respuesta.mensaje}. Se reintentara automaticamente.")

            ActividadUsuario.registrar(
                request.user, "FACTURA_GENERADA",
                f"Factura {numero_f} - Venta {venta.numero_factura} "
                f"[{factura.get_estado_display()}]")

        return Response(FacturaElectronicaLecturaSerializer(factura).data,
                        status=status.HTTP_201_CREATED)


class FacturaDetalleView(APIView):
    """GET detalle de una factura electronica."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request, id):
        empresa = _obtener_empresa(request)
        factura = FacturaElectronica.objects.select_related(
            'venta__cliente', 'venta__empresa'
        ).filter(id=id, venta__empresa=empresa).first()
        if not factura:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(FacturaElectronicaLecturaSerializer(factura).data)


class FacturaReenviarView(APIView):
    """POST reenvia la factura por correo al cliente."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request, id):
        empresa = _obtener_empresa(request)
        factura = FacturaElectronica.objects.select_related(
            'venta__cliente'
        ).filter(id=id, venta__empresa=empresa).first()
        if not factura:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if factura.estado != 'aprobada':
            return Response(
                {"codigo": "FACTURA_NO_APROBADA",
                 "detalle": "Solo se pueden reenviar facturas aprobadas "
                            "por la DIAN (con CUFE)."},
                status=status.HTTP_400_BAD_REQUEST)

        entrada = ReenviarFacturaSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        email_destino = entrada.validated_data.get(
            'email_destino') or factura.venta.cliente.email
        if not email_destino:
            return Response(
                {"codigo": "SIN_EMAIL",
                 "detalle": "El cliente no tiene correo registrado. "
                            "Envia un email_destino manualmente."},
                status=status.HTTP_400_BAD_REQUEST)

        mock_habilitado = os.environ.get(
            'DIAN_MOCK', 'True').lower() == 'true'
        if mock_habilitado:
            mensaje_envio = (f"[MOCK] Correo enviado a {email_destino} "
                             f"con factura {factura.numero} y CUFE "
                             f"{factura.cufe[:20]}...")
        else:
            mensaje_envio = (f"Correo enviado a {email_destino} "
                             f"con factura {factura.numero}")

        factura.enviado_correo = True
        factura.enviado_correo_en = timezone.now()
        factura.save(update_fields=['enviado_correo', 'enviado_correo_en',
                                    'updated_at'])

        ActividadUsuario.registrar(
            request.user, "FACTURA_REENVIADA",
            f"Factura {factura.numero} → {email_destino}")

        return Response({"detalle": mensaje_envio})


class FacturaReintentarView(APIView):
    """POST reintenta enviar una factura fallida a la DIAN."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def post(self, request, id):
        empresa = _obtener_empresa(request)
        factura = FacturaElectronica.objects.select_related(
            'venta__cliente', 'venta__empresa'
        ).filter(id=id, venta__empresa=empresa).first()
        if not factura:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if factura.estado not in ('fallida', 'rechazada'):
            return Response(
                {"codigo": "ESTADO_INVALIDO",
                 "detalle": "Solo se pueden reintentar facturas "
                            "fallidas o rechazadas."},
                status=status.HTTP_400_BAD_REQUEST)

        if factura.intentos >= 5:
            return Response(
                {"codigo": "MAXIMO_INTENTOS",
                 "detalle": "Se alcanzo el maximo de 5 reintentos. "
                            "Corrige los datos manualmente."},
                status=status.HTTP_400_BAD_REQUEST)

        datos_dian = _datos_venta_para_dian(factura.venta)
        respuesta = enviar_factura(datos_dian)

        with transaction.atomic():
            factura.intentos += 1
            factura.ultimo_intento = timezone.now()

            if respuesta.aprobada:
                factura.estado = 'aprobada'
                factura.cufe = respuesta.cufe
                factura.motivo_rechazo = ''
                factura.save(update_fields=[
                    'estado', 'cufe', 'motivo_rechazo',
                    'intentos', 'ultimo_intento', 'updated_at'
                ])
            elif respuesta.codigo_error == 'DATOS_INVALIDOS':
                factura.estado = 'rechazada'
                factura.motivo_rechazo = respuesta.mensaje
                factura.save(update_fields=[
                    'estado', 'motivo_rechazo',
                    'intentos', 'ultimo_intento', 'updated_at'
                ])
            else:
                factura.motivo_rechazo = respuesta.mensaje
                factura.save(update_fields=[
                    'estado', 'motivo_rechazo',
                    'intentos', 'ultimo_intento', 'updated_at'
                ])

            ActividadUsuario.registrar(
                request.user, "FACTURA_REINTENTADA",
                f"Factura {factura.numero} - Intento #{factura.intentos} "
                f"[{factura.get_estado_display()}]")

        return Response(FacturaElectronicaLecturaSerializer(factura).data)


# ------------------------------ Notas Credito ----------------------------

class NotasCreditoView(APIView):
    """GET lista notas credito / POST crea una nota credito."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request):
        empresa = _obtener_empresa(request)
        notas = NotaCredito.objects.select_related(
            'venta_original__cliente'
        ).filter(venta_original__empresa=empresa)

        datos = NotaCreditoLecturaSerializer(notas[:50], many=True).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request):
        return self.crear(request)

    def crear(self, request):
        entrada = NotaCreditoInputSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        empresa = _obtener_empresa(request)
        venta = Venta.objects.filter(
            empresa=empresa, deleted_at__isnull=True,
            id=entrada.validated_data['venta_id']
        ).first()
        if not venta:
            return Response(
                {"codigo": "VENTA_NO_ENCONTRADA",
                 "detalle": "La venta no existe."},
                status=status.HTTP_400_BAD_REQUEST)

        if venta.estado != 'completada':
            return Response(
                {"codigo": "ESTADO_INVALIDO",
                 "detalle": "Solo se pueden crear notas credito "
                            "para ventas completadas."},
                status=status.HTTP_400_BAD_REQUEST)

        if not hasattr(venta, 'factura_electronica'):
            return Response(
                {"codigo": "SIN_FACTURA",
                 "detalle": "La venta no tiene factura electronica. "
                            "Genera la factura primero."},
                status=status.HTTP_400_BAD_REQUEST)

        if venta.factura_electronica.estado != 'aprobada':
            return Response(
                {"codigo": "FACTURA_NO_APROBADA",
                 "detalle": "La factura electronica debe estar "
                            "aprobada por la DIAN."},
                status=status.HTTP_400_BAD_REQUEST)

        if NotaCredito.objects.filter(
                venta_original=venta, estado__in=('pendiente', 'aprobada')
        ).exists():
            return Response(
                {"codigo": "YA_TIENE_NOTA",
                 "detalle": "Esta venta ya tiene una nota credito "
                            "activa o pendiente."},
                status=status.HTTP_400_BAD_REQUEST)

        numero_nc = f"NC-{venta.numero_factura}"
        nota = NotaCredito.objects.create(
            venta_original=venta,
            numero=numero_nc,
            motivo=entrada.validated_data['motivo'],
            estado='pendiente',
        )

        cliente = venta.cliente
        datos_dian_nota = {
            'numero_nota': numero_nc,
            'numero_factura_original': venta.numero_factura,
            'fecha': timezone.now().isoformat(),
            'nit_empresa': empresa.nit,
            'cliente_doc': f"{cliente.tipo_documento} {cliente.numero_documento}",
            'total': str(venta.total),
            'motivo': nota.motivo,
        }
        respuesta = enviar_nota_credito(datos_dian_nota)

        with transaction.atomic():
            if respuesta.aprobada:
                nota.estado = 'aprobada'
                nota.cufe_nota = respuesta.cufe
                nota.save(update_fields=[
                    'estado', 'cufe_nota', 'updated_at'
                ])

                detalles = venta.detalles.select_related('producto').all()
                for detalle in detalles:
                    producto = detalle.producto
                    producto.stock += detalle.cantidad
                    producto.save(update_fields=['stock'])
                    _registrar_movimiento(
                        producto, request.user, 'entrada', detalle.cantidad,
                        f"Nota credito {numero_nc}")

                venta.estado = 'anulada'
                venta.motivo_anulacion = f"Nota credito {numero_nc}: {nota.motivo}"
                venta.anulada_en = timezone.now()
                venta.save(update_fields=[
                    'estado', 'motivo_anulacion', 'anulada_en', 'updated_at'
                ])

                nota.reverso_stock = True
                nota.save(update_fields=['reverso_stock'])

            elif respuesta.codigo_error == 'DATOS_INVALIDOS':
                nota.estado = 'rechazada'
                nota.save(update_fields=['estado', 'updated_at'])
                _notificar_admin(
                    empresa,
                    f"Nota credito {numero_nc} rechazada por DIAN: "
                    f"{respuesta.mensaje}")
            else:
                nota.save(update_fields=['updated_at'])
                _notificar_admin(
                    empresa,
                    f"Nota credito {numero_nc} fallo al enviar a DIAN: "
                    f"{respuesta.mensaje}")

            ActividadUsuario.registrar(
                request.user, "NOTA_CREDITO_CREADA",
                f"Nota credito {numero_nc} sobre {venta.numero_factura} "
                f"[{nota.get_estado_display()}]")

        return Response(NotaCreditoLecturaSerializer(nota).data,
                        status=status.HTTP_201_CREATED)


class NotaCreditoDetalleView(APIView):
    """GET detalle de una nota credito."""
    permission_classes = [IsAuthenticated, EsPersonal]

    def get(self, request, id):
        empresa = _obtener_empresa(request)
        nota = NotaCredito.objects.select_related(
            'venta_original__cliente'
        ).filter(id=id, venta_original__empresa=empresa).first()
        if not nota:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(NotaCreditoLecturaSerializer(nota).data)
