"""Control de acceso por rol:
- fase 2: la administracion de seguridad queda reservada al ADMINISTRADOR.
- fase 3: clientes y productos los gestiona el personal interno
  (ADMINISTRADOR o EMPLEADO); el rol CLIENTE queda excluido."""

from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    message = "Solo el ADMINISTRADOR puede gestionar la seguridad."

    def has_permission(self, request, view) -> bool:
        perfil = getattr(request.user, "perfil", None)
        return bool(perfil and not perfil.deleted_at and perfil.rol.nombre == "ADMINISTRADOR")


class EsPersonal(BasePermission):
    """ADMINISTRADOR o EMPLEADO con cuenta activa (fase 3)."""

    message = "Solo el personal de la empresa (ADMINISTRADOR o EMPLEADO) puede hacer esto."

    ROLES_PERSONAL = {"ADMINISTRADOR", "EMPLEADO"}

    def has_permission(self, request, view) -> bool:
        perfil = getattr(request.user, "perfil", None)
        return bool(perfil and not perfil.deleted_at
                    and perfil.rol.nombre in self.ROLES_PERSONAL)


def TienePermiso(codigo: str):
    """Factory de permission class por permiso fino (fase Empleados).

    Consulta RolPermiso vía Perfil.tiene_permiso(), a diferencia de
    EsAdministrador/EsPersonal que solo miran el nombre del rol. Uso:
    `permission_classes = [TienePermiso("empleado.crear")]`.
    """

    class _TienePermiso(BasePermission):
        message = f"No tiene el permiso '{codigo}' para esta accion."

        def has_permission(self, request, view) -> bool:
            perfil = getattr(request.user, "perfil", None)
            return bool(perfil and not perfil.deleted_at and perfil.tiene_permiso(codigo))

    _TienePermiso.__name__ = f"TienePermiso_{codigo.replace('.', '_')}"
    return _TienePermiso
