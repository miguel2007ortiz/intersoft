"""Rutas de la fase 4: ventas POS, inventario y alertas (personal interno).
Se monta en intersoft/urls.py bajo 'api/' -> /api/ventas/, /api/inventario/, /api/alertas/."""

from django.urls import path

from . import views_ventas

urlpatterns = [
    # Ventas POS
    path("ventas/", views_ventas.VentasView.as_view()),
    path("ventas/pos/", views_ventas.VentaPOSView.as_view()),
    path("ventas/<uuid:id>/", views_ventas.VentaDetalleView.as_view()),
    path("ventas/<uuid:id>/anular/", views_ventas.VentaDetalleView.as_view()),

    # Inventario
    path("inventario/", views_ventas.InventarioView.as_view()),
    path("inventario/productos/", views_ventas.InventarioProductosView.as_view()),
    path("inventario/<uuid:id>/ajustar/", views_ventas.InventarioView.as_view()),

    # Alertas
    path("alertas/", views_ventas.AlertasView.as_view()),
    path("alertas/<uuid:id>/revisar/", views_ventas.AlertasView.as_view()),
    path("alertas/<uuid:id>/actualizar-stock/", views_ventas.AlertaActualizarStockView.as_view()),
]
