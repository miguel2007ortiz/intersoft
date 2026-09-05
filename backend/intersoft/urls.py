from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('cuentas.urls')),
    path('api/seguridad/', include('cuentas.urls_admin')),  # fase 2: solo ADMINISTRADOR
    path('api/', include('core.urls_catalogo')),  # fase 3: clientes y productos (personal)
    path('api/', include('core.urls_ventas')),  # fase 4: ventas POS, inventario y alertas
    path('api/', include('core.urls_tienda')),  # fase 5: tienda virtual, carrito y checkout
    path('api/', include('core.urls_facturacion')),  # fase 6: facturacion DIAN y notas credito
    path('api/', include('core.urls_dashboard')),  # fase 7: dashboard de analitica (ADMIN)
    path('api/', include('core.urls_reportes')),  # fase 7: reportes y exportacion (ADMIN)
    path('api/', include('core.urls_ia')),  # fase 8: asistente IA (ADMIN y EMPLEADO)
    path('api/', include('core.urls_monitoreo')),  # fase 9: camaras y notificaciones (ADMIN)
    path('api/', include('core.urls_empleados')),  # modulo Empleados (personal interno)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "InterSoft - Administracion"
admin.site.site_title = "InterSoft Admin"
admin.site.index_title = "Panel de Gestion Empresarial"
