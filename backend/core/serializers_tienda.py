"""Serializers de la fase 5: tienda virtual, carrito y checkout."""

from decimal import Decimal

from django.db import models
from rest_framework import serializers

from .models import (Carrito, CarritoItem, Cliente, ComentarioProducto,
                     Cupon, Favorito, Producto, Categoria, Venta)
from .serializers_ventas import DetalleVentaLecturaSerializer


# ------------------------------ Catálogo ---------------------------------

class ProductoTiendaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    empresa_id = serializers.CharField(source='empresa.id', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    stock = serializers.SerializerMethodField()
    promedio_calificacion = serializers.SerializerMethodField()
    total_comentarios = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ["id", "nombre", "sku", "precio", "stock",
                  "categoria", "categoria_nombre", "imagen", "descripcion",
                  "empresa_id", "empresa_nombre", "created_at",
                  "promedio_calificacion", "total_comentarios"]

    def get_stock(self, obj):
        # Ocultar el stock real a visitantes anonimos de la tienda publica.
        if self.context.get("anonimo"):
            return None
        return obj.stock

    def get_promedio_calificacion(self, obj):
        # Usa la anotacion del queryset si esta disponible (evita N+1 en
        # listados); si no, calcula al vuelo (ej. detalle de un solo producto).
        if hasattr(obj, '_promedio_calificacion'):
            promedio = obj._promedio_calificacion
        else:
            promedio = obj.comentarios.aggregate(models.Avg('calificacion'))['calificacion__avg']
        return round(promedio, 1) if promedio is not None else None

    def get_total_comentarios(self, obj):
        if hasattr(obj, '_total_comentarios'):
            return obj._total_comentarios
        return obj.comentarios.count()


# --------------------------- Comentarios ----------------------------------

class ComentarioProductoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)

    class Meta:
        model = ComentarioProducto
        fields = ["id", "usuario_nombre", "calificacion", "comentario", "created_at"]
        read_only_fields = ["id", "usuario_nombre", "created_at"]


class ComentarioProductoEscrituraSerializer(serializers.Serializer):
    calificacion = serializers.IntegerField(min_value=1, max_value=5)
    comentario = serializers.CharField(required=False, allow_blank=True,
                                       max_length=1000, default="")


# ------------------------------ Favoritos ----------------------------------

class FavoritoSerializer(serializers.ModelSerializer):
    """Un favorito con el producto serializado para la ui del marketplace."""
    producto_obj = ProductoTiendaSerializer(source='producto', read_only=True)

    class Meta:
        model = Favorito
        fields = ["id", "producto", "producto_obj", "created_at"]
        read_only_fields = ["id", "producto_obj", "created_at"]


class CategoriaTiendaSerializer(serializers.ModelSerializer):
    productos_count = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ["id", "nombre", "productos_count"]

    def get_productos_count(self, obj):
        # Usa la anotacion num_productos del queryset (Fase 6) si existe.
        if hasattr(obj, "num_productos"):
            return obj.num_productos
        return obj.productos.filter(activo=True, deleted_at__isnull=True).count()


# ------------------------------ Cupón ------------------------------------

class CuponSerializer(serializers.ModelSerializer):
    esta_vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cupon
        fields = ["id", "codigo", "porcentaje", "activo",
                  "fecha_inicio", "fecha_fin", "esta_vigente"]


class CuponValidarSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=30)


# ------------------------------ Carrito ----------------------------------

class CarritoItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_precio = serializers.DecimalField(source='producto.precio',
                                               max_digits=12, decimal_places=2,
                                               read_only=True)
    producto_stock = serializers.IntegerField(source='producto.stock', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CarritoItem
        fields = ["id", "producto", "producto_nombre", "producto_precio",
                  "producto_stock", "cantidad", "subtotal"]

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class CarritoSerializer(serializers.ModelSerializer):
    items = CarritoItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.SerializerMethodField()
    descuento = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Carrito
        fields = ["id", "items", "total_items", "subtotal",
                  "descuento", "total", "created_at"]

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def get_descuento(self, obj):
        cupon = getattr(obj, 'cupon', None)
        if cupon and cupon.esta_vigente:
            return str(obj.subtotal * cupon.porcentaje / Decimal('100'))
        return '0'

    def get_total(self, obj):
        subtotal = obj.subtotal
        cupon = getattr(obj, 'cupon', None)
        if cupon and cupon.esta_vigente:
            descuento = subtotal * cupon.porcentaje / Decimal('100')
            return str(max(subtotal - descuento, Decimal('0')))
        return str(subtotal)


class CarritoItemInputSerializer(serializers.Serializer):
    producto = serializers.UUIDField()
    cantidad = serializers.IntegerField(min_value=1)


class CarritoCuponSerializer(serializers.Serializer):
    cupon_id = serializers.UUIDField(required=False, allow_null=True)


# ------------------------------ Comprador ---------------------------------

class CompletarCompradorSerializer(serializers.Serializer):
    """Datos minimos para vincular al usuario autenticado (admin, empleado o
    cliente) con un Cliente del marketplace (empresa=None), sin pasar por un
    registro aparte. Nombre y email se toman de la cuenta ya existente; solo
    se piden el documento y la direccion de envio."""
    tipo_documento = serializers.ChoiceField(choices=Cliente.TIPO_DOC_CHOICES, default='CC')
    numero_documento = serializers.CharField(min_length=3, max_length=20)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    direccion = serializers.CharField(required=False, allow_blank=True, default='')
    ciudad = serializers.CharField(max_length=80, required=False, allow_blank=True, default='')

    def validate(self, datos):
        tipo = datos.get("tipo_documento", "CC")
        numero = datos.get("numero_documento")
        # Documento unico entre los compradores del marketplace (empresa=None).
        if Cliente.objects.filter(empresa__isnull=True, deleted_at__isnull=True,
                                  tipo_documento=tipo, numero_documento=numero).exists():
            raise serializers.ValidationError({
                "numero_documento": "El documento ya esta registrado para un comprador.",
            })
        return datos

    def create(self, validated_data):
        usuario = self.context["usuario"]
        nombre = usuario.get_full_name().strip() or usuario.email
        return Cliente.objects.create(
            usuario=usuario, empresa=None, nombre=nombre, email=usuario.email,
            **validated_data,
        )


# ------------------------------ Pedidos del comprador ---------------------

class PedidoCompradorSerializer(serializers.ModelSerializer):
    """Una venta vista desde el comprador del marketplace: agrega el nombre
    de la empresa vendedora (el comprador no ve el resto de datos internos
    de la venta, solo lo que le corresponde como pedido)."""
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    detalles = DetalleVentaLecturaSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = ["id", "numero_factura", "fecha", "empresa_nombre",
                  "subtotal", "descuento", "total", "estado",
                  "metodo_pago", "detalles", "created_at"]
