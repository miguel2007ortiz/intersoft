"""Rutas de la app 'core' de InterSoft."""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Autenticación
    path('registro/', views.registro_empresario, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Productos
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/nuevo/', views.crear_producto, name='crear_producto'),
    path('productos/<uuid:pk>/editar/', views.editar_producto, name='editar_producto'),

    # Clientes
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/nuevo/', views.crear_cliente, name='crear_cliente'),

    # Ventas
    path('ventas/', views.lista_ventas, name='lista_ventas'),
    path('ventas/nueva/', views.crear_venta, name='crear_venta'),
]
