"""Control de acceso de la fase 2: la administracion de seguridad
(usuarios y roles) queda reservada al rol ADMINISTRADOR."""

from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    message = "Solo el ADMINISTRADOR puede gestionar la seguridad."

    def has_permission(self, request, view) -> bool:
        perfil = getattr(request.user, "perfil", None)
        return bool(perfil and not perfil.deleted_at and perfil.rol.nombre == "ADMINISTRADOR")
