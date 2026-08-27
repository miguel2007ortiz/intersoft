"""Rutas de la fase 7: reportes de administracion (solo ADMINISTRADOR).
Se monta en intersoft/urls.py bajo 'api/' -> /api/reportes/*."""

from django.urls import path

from . import views_reportes

urlpatterns = [
    path("reportes/tipos/", views_reportes.TiposReporteView.as_view()),
    path("reportes/vista/", views_reportes.ReporteVistaView.as_view()),
    path("reportes/exportar/", views_reportes.ReporteExportarView.as_view()),
]
