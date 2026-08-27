"""Rutas de la fase 5: tienda virtual, carrito y checkout.
Se monta en intersoft/urls.py bajo 'api/' -> /api/tienda/..."""

from django.urls import path

from . import views_tienda

urlpatterns = [
    # Catálogo público (sin auth)
    path("tienda/catalogo/", views_tienda.CatalogoPublicoView.as_view()),
    path("tienda/catalogo/<uuid:id>/", views_tienda.CatalogoProductoDetailView.as_view()),

    # Cupones
    path("tienda/cupones/", views_tienda.CuponesView.as_view()),
    path("tienda/cupones/validar/", views_tienda.CuponValidarView.as_view()),

    # Carrito (requiere auth)
    path("tienda/carrito/", views_tienda.CarritoView.as_view()),
    path("tienda/carrito/items/", views_tienda.CarritoItemView.as_view()),
    path("tienda/carrito/items/<uuid:item_id>/", views_tienda.CarritoItemView.as_view()),
    path("tienda/carrito/cupon/", views_tienda.CarritoCuponView.as_view()),

    # Checkout
    path("tienda/checkout/", views_tienda.CheckoutView.as_view()),

    # Pedidos del comprador
    path("tienda/pedidos/", views_tienda.MisPedidosView.as_view()),
]
