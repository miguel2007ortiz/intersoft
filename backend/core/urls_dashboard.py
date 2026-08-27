"""Rutas de la fase 7: dashboard de analitica (solo ADMINISTRADOR).
Se monta en intersoft/urls.py bajo 'api/' -> /api/dashboard/*."""

from django.urls import path

from . import views_dashboard

urlpatterns = [
    path("dashboard/resumen/", views_dashboard.DashboardResumenView.as_view()),
    path("dashboard/ventas/", views_dashboard.DashboardVentasView.as_view()),
    path("dashboard/top-productos/", views_dashboard.DashboardTopProductosView.as_view()),
    path("dashboard/clientes-frecuentes/",
         views_dashboard.DashboardClientesFrecuentesView.as_view()),
    path("dashboard/inventario/", views_dashboard.DashboardInventarioView.as_view()),
    path("dashboard/categorias/", views_dashboard.DashboardCategoriasView.as_view()),
]
