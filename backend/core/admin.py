from django.contrib import admin
from .models import (Empresa, Categoria, Producto, Cliente, Venta,
                     DetalleVenta, MovimientoInventario, Notificacion)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'plan', 'activa', 'created_at')
    list_filter = ('plan', 'activa', 'created_at')
    search_fields = ('nombre', 'nit', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at')


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa')
    list_filter = ('empresa',)
    search_fields = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sku', 'categoria', 'precio', 'stock', 'stock_bajo', 'activo')
    list_filter = ('empresa', 'categoria', 'activo')
    search_fields = ('nombre', 'sku')
    readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at')
    list_editable = ('precio', 'stock', 'activo')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_documento', 'numero_documento', 'email', 'empresa', 'total_compras')
    list_filter = ('empresa', 'tipo_documento')
    search_fields = ('nombre', 'numero_documento', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at', 'total_compras')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'cliente', 'total', 'estado', 'metodo_pago', 'fecha')
    list_filter = ('empresa', 'estado', 'metodo_pago', 'fecha')
    search_fields = ('numero_factura', 'cliente__nombre')
    readonly_fields = ('id', 'numero_factura', 'fecha', 'created_at', 'updated_at', 'deleted_at')
    date_hierarchy = 'fecha'
    inlines = [DetalleVentaInline]


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'producto', 'cantidad', 'precio_unitario', 'subtotal')
    search_fields = ('venta__numero_factura', 'producto__nombre')


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'cantidad', 'usuario', 'motivo', 'created_at')
    list_filter = ('tipo', 'producto__empresa')
    search_fields = ('producto__nombre', 'motivo')
    readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at')
    date_hierarchy = 'created_at'


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('mensaje', 'usuario', 'leida', 'created_at')
    list_filter = ('leida',)
    search_fields = ('mensaje', 'usuario__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
