"""Serializers de la fase 5: tienda virtual, carrito y checkout."""

from decimal import Decimal

from rest_framework import serializers

from .models import Carrito, CarritoItem, Cupon, Producto, Categoria


# ------------------------------ Catálogo ---------------------------------

class ProductoTiendaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    stock = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ["id", "nombre", "sku", "precio", "stock",
                  "categoria", "categoria_nombre", "imagen", "descripcion"]

    def get_stock(self, obj):
        # Ocultar el stock real a visitantes anonimos de la tienda publica.
        if self.context.get("anonimo"):
            return None
        return obj.stock


class CategoriaTiendaSerializer(serializers.ModelSerializer):
    productos_count = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ["id", "nombre", "productos_count"]

    def get_productos_count(self, obj):
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
