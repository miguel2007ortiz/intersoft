"""Serializers de la fase 4: ventas POS, inventario y alertas.

Convenciones del proyecto:
- respuestas de error con {"codigo", "detalle", "errores"};
- todo dentro de transaction.atomic() para garantizar ACID;
- stock >= 0 (ademas del CHECK de BD);
- productos desactivados no generan alertas aunque tengan stock bajo."""

from decimal import Decimal

from rest_framework import serializers

from .models import (DetalleVenta, Envio, MovimientoInventario, Venta)


# ------------------------------ Ventas ------------------------------------

class DetalleVentaLecturaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    subtotal_linea = serializers.SerializerMethodField()

    class Meta:
        model = DetalleVenta
        fields = ["id", "producto", "producto_nombre", "producto_sku",
                  "cantidad", "precio_unitario", "subtotal_linea"]

    def get_subtotal_linea(self, obj):
        return str(obj.subtotal)


class DetalleVentaEscrituraSerializer(serializers.Serializer):
    producto = serializers.UUIDField()
    cantidad = serializers.IntegerField(min_value=1)


class VentaLecturaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cliente_documento = serializers.SerializerMethodField()
    vendedor_nombre = serializers.SerializerMethodField()
    detalles = DetalleVentaLecturaSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = ["id", "numero_factura", "fecha", "cliente", "cliente_nombre",
                  "cliente_documento", "vendedor", "vendedor_nombre",
                  "subtotal", "descuento", "total", "estado", "metodo_pago",
                  "notas", "motivo_anulacion", "anulada_en", "detalles",
                  "total_items", "created_at"]

    def get_cliente_documento(self, obj):
        c = obj.cliente
        return f"{c.tipo_documento} {c.numero_documento}"

    def get_vendedor_nombre(self, obj):
        # vendedor.perfil.usuario es el mismo User que obj.vendedor, asi que
        # el nombre sale directo del registro ya cargado (Fase 6: sin N+1).
        if not obj.vendedor:
            return None
        return obj.vendedor.get_full_name() or obj.vendedor.email

    def get_total_items(self, obj):
        return sum(d.cantidad for d in obj.detalles.all())


class VentaPOSInputSerializer(serializers.Serializer):
    """Entrada para crear una venta desde el POS."""
    cliente = serializers.UUIDField()
    metodo_pago = serializers.ChoiceField(choices=Venta.METODO_PAGO_CHOICES,
                                          default='efectivo')
    descuento = serializers.DecimalField(max_digits=12, decimal_places=2,
                                         default=Decimal('0'), min_value=0)
    notas = serializers.CharField(required=False, default='')
    detalles = DetalleVentaEscrituraSerializer(many=True, min_length=1)


class AnulacionSerializer(serializers.Serializer):
    """Entrada para anular una venta."""
    motivo = serializers.CharField(min_length=3)


class AjusteInventarioSerializer(serializers.Serializer):
    """Entrada para ajuste manual de inventario."""
    producto = serializers.UUIDField()
    cantidad = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=[('entrada', 'Entrada'), ('salida', 'Salida')])
    motivo = serializers.CharField(min_length=3)


class AlertaReabastecerSerializer(serializers.Serializer):
    """Entrada opcional para reabastecer desde una alerta de stock bajo.
    Sin `cantidad`, la vista calcula cuanto agregar para superar el minimo."""
    cantidad = serializers.IntegerField(min_value=1, required=False)


# ------------------------------ Envios (fase 10) --------------------------

class EnvioLecturaSerializer(serializers.ModelSerializer):
    """Vista de envio para el personal interno (empleado/admin de la
    empresa vendedora): todos los campos, incluye numero_factura de la venta
    para ubicarlo en listas sin pedir la venta por separado."""
    numero_factura = serializers.CharField(source='venta.numero_factura', read_only=True)
    cliente_nombre = serializers.CharField(source='venta.cliente.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Envio
        fields = ["id", "venta", "numero_factura", "cliente_nombre",
                  "direccion", "ciudad", "departamento", "transportadora",
                  "numero_guia", "estado", "estado_display",
                  "fecha_despacho", "fecha_entrega_estimada",
                  "fecha_entrega_real", "notas", "created_at", "updated_at"]
        read_only_fields = ["id", "venta", "created_at", "updated_at"]


class EnvioEstadoInputSerializer(serializers.Serializer):
    """Entrada para actualizar un envio. `estado` es opcional: se puede
    guardar transportadora/numero_guia/notas sin forzar un cambio de estado
    (la transicion real la valida Envio.cambiar_estado, no este serializer)."""
    estado = serializers.ChoiceField(choices=Envio.ESTADO_CHOICES, required=False)
    transportadora = serializers.CharField(max_length=80, required=False, allow_blank=True)
    numero_guia = serializers.CharField(max_length=80, required=False, allow_blank=True)
    fecha_entrega_estimada = serializers.DateField(required=False, allow_null=True)
    notas = serializers.CharField(required=False, allow_blank=True)


# ------------------------------ Inventario --------------------------------

class MovimientoInventarioLecturaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoInventario
        fields = ["id", "producto", "producto_nombre", "producto_sku",
                  "usuario", "usuario_nombre", "tipo", "cantidad",
                  "motivo", "created_at"]

    def get_usuario_nombre(self, obj):
        if not obj.usuario:
            return None
        return obj.usuario.get_full_name() or obj.usuario.email
