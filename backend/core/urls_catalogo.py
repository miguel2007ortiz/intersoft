"""Rutas de la fase 3: clientes, productos y categorias (personal interno).
Se monta en intersoft/urls.py bajo 'api/' -> /api/clientes/, /api/productos/."""

from django.urls import path

from . import views_catalogo

urlpatterns = [
    path("clientes/", views_catalogo.ClientesView.as_view()),
    path("clientes/<uuid:id>/", views_catalogo.ClienteDetalleView.as_view()),

    path("productos/", views_catalogo.ProductosView.as_view()),
    path("productos/<uuid:id>/",
         views_catalogo.ProductoDetalleView.as_view()),
    path("productos/<uuid:id>/<str:accion>/",
         views_catalogo.ProductoEstadoView.as_view()),

    path("categorias/", views_catalogo.CategoriasView.as_view()),
]
