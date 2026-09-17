"""Serializers de la fase 6: facturacion electronica DIAN y notas credito."""

from rest_framework import serializers

from .models import FacturaElectronica, NotaCredito


class ArchivosComprobanteMixin(serializers.Serializer):
    """Expone `pdf` y `xml` como la URL del endpoint que los sirve.

    Antes se devolvia la ruta del `FileField`, es decir `/media/facturas/...`.
    Eso traia dos problemas:

    1. Relativa. El panel se sirve desde otro origen que la API en desarrollo,
       asi que el navegador la pedia al servidor de Angular y respondia
       "Cannot GET /media/...".
    2. Publica. MEDIA no pasa por la autenticacion de Django y las rutas son
       adivinables (`FE-<numero_factura>.pdf`), de modo que cualquiera con el
       enlace podia bajarse la facturacion de otra empresa.

    Ahora apunta a `/api/.../archivo/<tipo>/`, que exige sesion y filtra por
    empresa. Devuelve `None` cuando el comprobante todavia no existe, para que
    el frontend siga pudiendo ocultar el boton.
    """

    RUTA_ARCHIVO = ""   # la define cada serializer concreto

    pdf = serializers.SerializerMethodField()
    xml = serializers.SerializerMethodField()

    def _url_archivo(self, obj, tipo):
        if not getattr(obj, tipo, None):
            return None
        ruta = self.RUTA_ARCHIVO.format(id=obj.id, tipo=tipo)
        request = self.context.get("request")
        return request.build_absolute_uri(ruta) if request is not None else ruta

    def get_pdf(self, obj):
        return self._url_archivo(obj, "pdf")

    def get_xml(self, obj):
        return self._url_archivo(obj, "xml")


class FacturaElectronicaLecturaSerializer(ArchivosComprobanteMixin,
                                          serializers.ModelSerializer):
    RUTA_ARCHIVO = "/api/facturacion/{id}/archivo/{tipo}/"

    venta_numero = serializers.CharField(source='venta.numero_factura', read_only=True)
    cliente_nombre = serializers.CharField(source='venta.cliente.nombre', read_only=True)
    cliente_documento = serializers.SerializerMethodField()
    venta_total = serializers.DecimalField(source='venta.total', max_digits=12,
                                           decimal_places=2, read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = FacturaElectronica
        fields = ["id", "venta", "venta_numero", "cliente_nombre", "cliente_documento",
                  "venta_total", "numero", "cufe", "estado", "estado_display",
                  "motivo_rechazo", "pdf", "xml", "intentos", "ultimo_intento",
                  "enviado_correo", "enviado_correo_en", "created_at"]

    def get_cliente_documento(self, obj):
        c = obj.venta.cliente
        return f"{c.tipo_documento} {c.numero_documento}"


class NotaCreditoLecturaSerializer(ArchivosComprobanteMixin,
                                   serializers.ModelSerializer):
    RUTA_ARCHIVO = "/api/notas-credito/{id}/archivo/{tipo}/"

    venta_numero = serializers.CharField(source='venta_original.numero_factura', read_only=True)
    cliente_nombre = serializers.CharField(source='venta_original.cliente.nombre', read_only=True)
    venta_total = serializers.DecimalField(source='venta_original.total', max_digits=12,
                                           decimal_places=2, read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = NotaCredito
        fields = ["id", "venta_original", "venta_numero", "cliente_nombre",
                  "venta_total", "numero", "cufe_nota", "estado", "estado_display",
                  "motivo", "pdf", "xml", "reverso_stock", "created_at"]


class GenerarFacturaSerializer(serializers.Serializer):
    """Entrada para generar factura electronica de una venta."""
    venta_id = serializers.UUIDField()


class NotaCreditoInputSerializer(serializers.Serializer):
    """Entrada para crear una nota credito."""
    venta_id = serializers.UUIDField()
    motivo = serializers.CharField(min_length=5)


class ReenviarFacturaSerializer(serializers.Serializer):
    """Entrada para reenviar factura por correo."""
    email_destino = serializers.EmailField(required=False)


class ReintentarFacturaSerializer(serializers.Serializer):
    """Entrada para reintentar envio a DIAN de una factura fallida."""
    pass
