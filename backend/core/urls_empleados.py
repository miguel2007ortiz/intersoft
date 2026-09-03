"""Rutas del modulo Empleados (personal interno).
Se monta en intersoft/urls.py bajo 'api/' -> /api/empleados/.
Aditivo: no reemplaza /api/seguridad/usuarios/ (fase 2)."""

from django.urls import path

from . import views_empleados

urlpatterns = [
    path("empleados/", views_empleados.EmpleadosView.as_view()),
    path("empleados/<uuid:id>/", views_empleados.EmpleadoDetalleView.as_view()),
    path("empleados/<uuid:id>/password/", views_empleados.EmpleadoPasswordView.as_view()),
    path("empleados/<uuid:id>/<str:accion>/",
         views_empleados.EmpleadoEstadoView.as_view()),
]
