"""
URLs principales de InterSoft.

Enruta las peticiones hacia el admin de Django y hacia la app 'core'.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # Todas las rutas de negocio viven en core
]

# Servir archivos media (imágenes) en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Personalización del panel de administración
admin.site.site_header = "InterSoft — Administración"
admin.site.site_title = "InterSoft Admin"
admin.site.index_title = "Panel de Gestión Empresarial"
