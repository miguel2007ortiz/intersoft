"""Rutas de la fase 6: facturacion electronica DIAN y notas credito.
Se monta en intersoft/urls.py bajo 'api/' -> /api/facturacion/..."""

from django.urls import path

from . import views_facturacion

urlpatterns = [
    # Facturas electronicas
    path("facturacion/", views_facturacion.FacturasView.as_view()),
    path("facturacion/<uuid:id>/", views_facturacion.FacturaDetalleView.as_view()),
    path("facturacion/<uuid:id>/reenviar/", views_facturacion.FacturaReenviarView.as_view()),
    path("facturacion/<uuid:id>/reintentar/", views_facturacion.FacturaReintentarView.as_view()),

    # Notas credito
    path("notas-credito/", views_facturacion.NotasCreditoView.as_view()),
    path("notas-credito/<uuid:id>/", views_facturacion.NotaCreditoDetalleView.as_view()),
]
