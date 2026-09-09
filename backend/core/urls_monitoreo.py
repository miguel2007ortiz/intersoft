"""Rutas de la fase 9: monitoreo de camaras y centro de notificaciones.

Solo ADMINISTRADOR. Se monta en intersoft/urls.py bajo 'api/':
  * /api/camaras/                       lista / crea camaras
  * /api/camaras/<uuid:id>/             detalle / edicion / baja
  * /api/camaras/<uuid:id>/grabacion/   grabacion historica por fecha/hora
  * /api/camaras/<uuid:id>/grabaciones/ catalogo de grabaciones (paginado)
  * /api/notificaciones/                centro de notificaciones (activas)
  * /api/notificaciones/<uuid:id>/      marcar revisada / resuelta
"""

from django.urls import path

from . import views_monitoreo

urlpatterns = [
    path("camaras/", views_monitoreo.CamarasView.as_view()),
    path("camaras/<uuid:id>/", views_monitoreo.CamaraDetalleView.as_view()),
    path("camaras/<uuid:id>/grabacion/", views_monitoreo.CamaraGrabacionView.as_view()),
    path("camaras/<uuid:id>/grabaciones/", views_monitoreo.CamaraGrabacionesView.as_view()),
    path("notificaciones/", views_monitoreo.NotificacionesView.as_view()),
    path("notificaciones/<uuid:id>/", views_monitoreo.NotificacionDetalleView.as_view()),
]
