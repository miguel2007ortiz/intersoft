"""Control de acceso por rol:
- fase 2: la administracion de seguridad queda reservada al ADMINISTRADOR.
- fase 3: clientes y productos los gestiona el personal interno
  (ADMINISTRADOR o EMPLEADO); el rol CLIENTE queda excluido."""

from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    message = "Solo el ADMINISTRADOR puede gestionar la seguridad."

    def has_permission(self, request, view) -> bool:
        perfil = getattr(request.user, "perfil", None)
        # perfil.rol es PROTECT y no-nulo a nivel de modelo, pero un perfil
        # mal migrado/creado a mano (p. ej. via shell) puede tener rol_id
        # colgante; sin este guard, perfil.rol lanzaba AttributeError -> 500
        # en vez de negar el acceso.
        if not (perfil and not perfil.deleted_at and perfil.rol):
            return False
        # Ademas del rol base ADMINISTRADOR, acepta un rol personalizado
        # por-empresa que tenga el permiso de gestion de usuarios: antes
        # solo se comparaba perfil.rol.nombre, asi que un rol a medida con
        # permisos de administrador (asignables solo via roles.asignar,
        # exclusivo del ADMINISTRADOR) quedaba bloqueado de estas vistas
        # pese a tener realmente el permiso.
        return (perfil.rol.nombre == "ADMINISTRADOR"
                or perfil.tiene_permiso("usuarios.gestionar"))


class EsPersonal(BasePermission):
    """ADMINISTRADOR o EMPLEADO con cuenta activa (fase 3), o cualquier rol
    -incluido uno personalizado por-empresa- con al menos un permiso
    operativo asignado (el rol base CLIENTE no tiene ninguno)."""

    message = "Solo el personal de la empresa (ADMINISTRADOR o EMPLEADO) puede hacer esto."

    ROLES_PERSONAL = {"ADMINISTRADOR", "EMPLEADO"}

    def has_permission(self, request, view) -> bool:
        perfil = getattr(request.user, "perfil", None)
        if not (perfil and not perfil.deleted_at and perfil.rol):
            return False
        return (perfil.rol.nombre in self.ROLES_PERSONAL
                or perfil.rol.rol_permisos.exists())


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
