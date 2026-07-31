"""
Registro de modelos en el panel de administración de Django.

El admin es una de las mejores ventajas de Django: con pocas líneas
obtienes un CRUD completo con búsqueda, filtros y paginación.
"""

from django.contrib import admin
from .models import Empresa, Usuario, Categoria, Producto, Cliente, Venta, Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'empresa', 'es_propietario')
    list_filter = ('es_propietario', 'empresa')
    search_fields = ('user__username', 'empresa__nombre')


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'plan', 'activa', 'created_at')
    list_filter = ('plan', 'activa', 'created_at')
    search_fields = ('nombre', 'nit', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at')


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'empresa', 'rol', 'activo', 'ultimo_login')
    list_filter = ('empresa', 'rol', 'activo')
    search_fields = ('nombre', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at')


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
