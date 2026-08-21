"""Rutas de la fase 2: administracion de seguridad (solo ADMINISTRADOR).
Se monta bajo /api/seguridad/ desde intersoft/urls.py."""

from django.urls import path

from .views_admin import (
    PermisosCatalogoView, RolClonarView, RolDetalleView, RolesSeguridadView,
    UsuarioDesactivarView, UsuarioReactivarView, UsuarioSeguridadDetalleView,
    UsuariosSeguridadView,
)

urlpatterns = [
    # Usuarios
    path("usuarios/", UsuariosSeguridadView.as_view(), name="seguridad-usuarios"),
    path("usuarios/<uuid:id>/", UsuarioSeguridadDetalleView.as_view(), name="seguridad-usuario-detalle"),
    path("usuarios/<uuid:id>/desactivar/", UsuarioDesactivarView.as_view(), name="seguridad-usuario-desactivar"),
    path("usuarios/<uuid:id>/reactivar/", UsuarioReactivarView.as_view(), name="seguridad-usuario-reactivar"),

    # Roles
    path("roles/", RolesSeguridadView.as_view(), name="seguridad-roles"),
    path("roles/<uuid:id>/", RolDetalleView.as_view(), name="seguridad-rol-detalle"),
    path("roles/<uuid:id>/clonar/", RolClonarView.as_view(), name="seguridad-rol-clonar"),

    # Catalogo de permisos para asignar
    path("permisos/", PermisosCatalogoView.as_view(), name="seguridad-permisos"),
]
