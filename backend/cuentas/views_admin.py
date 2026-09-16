"""API de seguridad de la fase 2 (solo ADMINISTRADOR):
CRUD de usuarios, CRUD de roles con permisos, clonado de roles y
bloqueo de eliminacion de roles en uso. Toda accion queda auditada
en actividad_usuario."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Empresa

from .models import ActividadUsuario, Permiso, Perfil, Rol, RolPermiso
from .permissions import EsAdministrador
from .serializers_admin import (
    ROLES_DEL_SISTEMA, RolEscrituraSerializer, RolLecturaSerializer,
    UsuarioCreacionSerializer, UsuarioEdicionSerializer, UsuarioLecturaSerializer,
)

Usuario = get_user_model()


def respuesta_datos_invalidas(errores):
    return Response({"codigo": "DATOS_INVALIDOS",
                     "detalle": "Revisa los datos del formulario.",
                     "errores": errores}, status=status.HTTP_400_BAD_REQUEST)


def _limite_paginacion(valor, por_defecto=50, maximo=200):
    """Limite de filas a devolver, acotado a [1, maximo]."""
    try:
        return max(1, min(int(valor), maximo))
    except (TypeError, ValueError):
        return por_defecto


def perfiles_de_empresa(empresa: Empresa):
    return (Perfil.objects.filter(empresa=empresa, deleted_at__isnull=True)
            .select_related("usuario", "rol").order_by("usuario__first_name"))


def roles_visibles(empresa: Empresa):
    """Roles que una empresa puede ver y asignar: los globales del sistema
    (empresa=None) mas sus propios roles personalizados."""
    return Rol.objects.filter(Q(empresa=empresa) | Q(empresa__isnull=True))


def filtro_usuarios_activos(empresa: Empresa) -> Q:
    """Condicion de "usuario que cuenta" para un rol, vista desde `empresa`.

    Los roles base (ADMINISTRADOR, EMPLEADO, CLIENTE) son GLOBALES: sus
    `perfiles` incluyen los de todas las empresas. Sin el filtro por empresa,
    la pantalla de Roles contaba los perfiles de todos los tenants mientras
    la de Usuarios -- que si filtra -- mostraba solo los propios.
    """
    return Q(perfiles__empresa=empresa,
             perfiles__deleted_at__isnull=True,
             perfiles__usuario__is_active=True)


class UsuariosSeguridadView(APIView):
    """GET lista de cuentas de mi empresa / POST crea cuenta con rol."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        perfiles = perfiles_de_empresa(request.user.perfil.empresa)
        limite = _limite_paginacion(request.query_params.get('limite', 50))
        datos = UsuarioLecturaSerializer(perfiles[:limite], many=True).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request):
        entrada = UsuarioCreacionSerializer(
            data=request.data, context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidas(entrada.errors)

        datos = entrada.validated_data
        empresa = request.user.perfil.empresa
        rol = roles_visibles(empresa).get(nombre=datos["rol"])
        with transaction.atomic():
            partes = datos["nombre"].split(" ", 1)
            usuario = Usuario.objects.create_user(
                username=datos["email"], email=datos["email"],
                password=datos["password"], first_name=partes[0],
                last_name=partes[1] if len(partes) > 1 else "")
            perfil = Perfil.objects.create(usuario=usuario,
                                           empresa=empresa,
                                           rol=rol)
        ActividadUsuario.registrar(request.user, "USUARIO_CREADO",
                                   f"{usuario.email} ({perfil.rol.nombre})")
        return Response(UsuarioLecturaSerializer(perfil).data,
                        status=status.HTTP_201_CREATED)


class UsuarioSeguridadDetalleView(APIView):
    """GET detalle / PUT-PATCH edicion de nombre, correo, rol y contrasena."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def obtener_perfil(self, request, id):
        return (perfiles_de_empresa(request.user.perfil.empresa)
                .filter(id=id).first())

    def get(self, request, id):
        perfil = self.obtener_perfil(request, id)
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(UsuarioLecturaSerializer(perfil).data)

    def put(self, request, id):
        return self.editar(request, id, parcial=False)

    def patch(self, request, id):
        return self.editar(request, id, parcial=True)

    def editar(self, request, id, parcial: bool):
        perfil = self.obtener_perfil(request, id)
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        entrada = UsuarioEdicionSerializer(
            perfil, data=request.data, partial=parcial,
            context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidas(entrada.errors)

        datos = entrada.validated_data
        with transaction.atomic():
            usuario = perfil.usuario
            if "nombre" in datos:
                partes = datos["nombre"].split(" ", 1)
                usuario.first_name = partes[0]
                usuario.last_name = partes[1] if len(partes) > 1 else ""
            if "email" in datos:
                usuario.email = datos["email"]
                usuario.username = datos["email"]
            if datos.get("password"):
                usuario.set_password(datos["password"])
            usuario.save()
            if "rol" in datos:
                perfil.rol = roles_visibles(request.user.perfil.empresa).get(
                    nombre=datos["rol"])
                perfil.save(update_fields=["rol"])

        ActividadUsuario.registrar(request.user, "USUARIO_EDITADO",
                                   f"{usuario.email} -> rol {perfil.rol.nombre}")
        return Response(UsuarioLecturaSerializer(perfil).data)


class UsuarioDesactivarView(APIView):
    """POST desactiva la cuenta (borrado logico de acceso, no elimina datos)."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def post(self, request, id):
        perfil = (perfiles_de_empresa(request.user.perfil.empresa)
                  .filter(id=id).first())
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if perfil.usuario_id == request.user.id:
            return Response({"codigo": "AUTODESACTIVACION_PROHIBIDA",
                             "detalle": "No puedes desactivar tu propia cuenta."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not perfil.usuario.is_active:
            return Response({"codigo": "YA_DESACTIVADO",
                             "detalle": "La cuenta ya esta desactivada."},
                            status=status.HTTP_400_BAD_REQUEST)

        perfil.usuario.is_active = False
        perfil.usuario.save(update_fields=["is_active"])
        ActividadUsuario.registrar(request.user, "USUARIO_DESACTIVADO",
                                   perfil.usuario.email)
        return Response(UsuarioLecturaSerializer(perfil).data)


class UsuarioReactivarView(APIView):
    permission_classes = [IsAuthenticated, EsAdministrador]

    def post(self, request, id):
        perfil = (perfiles_de_empresa(request.user.perfil.empresa)
                  .filter(id=id).first())
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if perfil.usuario.is_active:
            return Response({"codigo": "YA_ACTIVO",
                             "detalle": "La cuenta ya esta activa."},
                            status=status.HTTP_400_BAD_REQUEST)

        perfil.usuario.is_active = True
        perfil.usuario.save(update_fields=["is_active"])
        perfil.reiniciar_intentos()
        ActividadUsuario.registrar(request.user, "USUARIO_REACTIVADO",
                                   perfil.usuario.email)
        return Response(UsuarioLecturaSerializer(perfil).data)


def asignar_permisos(rol: Rol, codigos: list) -> None:
    """Deja al rol exactamente con los permisos indicados (sincronizacion)."""
    RolPermiso.objects.filter(rol=rol).exclude(permiso__codigo__in=codigos).delete()
    for codigo in codigos:
        RolPermiso.objects.get_or_create(rol=rol,
                                         permiso=Permiso.objects.get(codigo=codigo))


class RolesSeguridadView(APIView):
    """GET catalogo de roles con sus permisos / POST crea un rol."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        empresa = request.user.perfil.empresa
        roles = (roles_visibles(empresa)
                 .annotate(total_usuarios_activos=Count(
                     "perfiles", filter=filtro_usuarios_activos(empresa)))
                 .prefetch_related("rol_permisos__permiso").order_by("nombre"))
        datos = RolLecturaSerializer(roles, many=True,
                                     context={"empresa": empresa}).data
        return Response({"resultados": datos, "total": len(datos)})

    def post(self, request):
        entrada = RolEscrituraSerializer(data=request.data,
                                         context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidas(entrada.errors)

        datos = entrada.validated_data
        with transaction.atomic():
            rol = Rol.objects.create(nombre=datos["nombre"],
                                     descripcion=datos.get("descripcion", ""),
                                     empresa=request.user.perfil.empresa)
            asignar_permisos(rol, datos.get("permisos", []))

        ActividadUsuario.registrar(request.user, "ROL_CREADO",
                                   f"{rol.nombre} ({len(datos.get('permisos', []))} permisos)")
        return Response(RolLecturaSerializer(
            rol, context={"empresa": request.user.perfil.empresa}).data,
            status=status.HTTP_201_CREATED)


class RolDetalleView(APIView):
    """GET / PUT-PATCH (nombre, descripcion y permisos) / DELETE.

    Estrategia de roles del sistema (ADMINISTRADOR, EMPLEADO, CLIENTE):
    son roles GLOBALES (empresa=None) compartidos por todos los tenants, por
    lo que se tratan como LECTURA-ONLY. Cualquier empresa puede VERLOS y
    ASIGNARLOS (y clonarlos como plantilla), pero NINGUN administrador puede
    renombrarlos, cambiar su descripcion, modificar sus permisos ni
    eliminarlos. Asi se evita que un tenant altere la autorizacion global de
    los demas (escalamiento transversal) y se garantiza la integridad del
    RBAC base del sistema. Los roles PERSONALIZADOS (empresa=None) no existen:
    los creados por un admin pertenecen a SU empresa y quedan aislados.
    """
    permission_classes = [IsAuthenticated, EsAdministrador]

    @staticmethod
    def obtener_rol(empresa, id):
        return (roles_visibles(empresa).filter(id=id)
                .prefetch_related("rol_permisos__permiso").first())

    def get(self, request, id):
        rol = self.obtener_rol(request.user.perfil.empresa, id)
        if rol is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(RolLecturaSerializer(
            rol, context={"empresa": request.user.perfil.empresa}).data)

    def put(self, request, id):
        return self.editar(request, id, parcial=False)

    def patch(self, request, id):
        return self.editar(request, id, parcial=True)

    def editar(self, request, id, parcial: bool):
        rol = self.obtener_rol(request.user.perfil.empresa, id)
        if rol is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Los roles del sistema son globales y compartidos por todos los
        # tenants: no se pueden editar (ni nombre, ni descripcion, ni
        # permisos) para impedir que una empresa altere la autorizacion de
        # las demas (requisito fase 3: aislamiento multiempresa).
        if rol.nombre in ROLES_DEL_SISTEMA:
            return Response({"codigo": "ROL_SISTEMA_LECTURA_ONLY",
                             "detalle": "Los roles base del sistema son de "
                                        "solo lectura: no se pueden editar."},
                            status=status.HTTP_400_BAD_REQUEST)

        entrada = RolEscrituraSerializer(rol, data=request.data, partial=parcial,
                                         context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidas(entrada.errors)

        datos = entrada.validated_data
        nombre_anterior = rol.nombre

        with transaction.atomic():
            if "nombre" in datos:
                rol.nombre = datos["nombre"]
            if "descripcion" in datos:
                rol.descripcion = datos["descripcion"]
            rol.save()
            if "permisos" in datos:
                asignar_permisos(rol, datos["permisos"])

        ActividadUsuario.registrar(request.user, "ROL_EDITADO",
                                   f"{nombre_anterior} -> {rol.nombre}")
        return Response(RolLecturaSerializer(
            rol, context={"empresa": request.user.perfil.empresa}).data)

    def delete(self, request, id):
        rol = self.obtener_rol(request.user.perfil.empresa, id)
        if rol is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if rol.nombre in ROLES_DEL_SISTEMA:
            return Response({"codigo": "ROL_SISTEMA_LECTURA_ONLY",
                             "detalle": "Los roles base del sistema no se "
                                        "pueden eliminar."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Solo los usuarios de MI empresa: un rol global lo comparten todos
        # los tenants y no debe contarse (ni revelarse) el uso ajeno.
        activos = Perfil.objects.filter(rol=rol,
                                        empresa=request.user.perfil.empresa,
                                        deleted_at__isnull=True,
                                        usuario__is_active=True).count()
        if activos > 0:
            # Regla fase 2: hay que reasignar los usuarios antes de borrar el rol
            return Response({"codigo": "ROL_CON_USUARIOS_ACTIVOS",
                             "detalle": f"Hay {activos} usuario(s) activo(s) con este rol. "
                                        "Reasignalos a otro rol antes de eliminarlo.",
                             "usuarios_activos": activos},
                            status=status.HTTP_400_BAD_REQUEST)

        nombre = rol.nombre
        try:
            with transaction.atomic():
                rol.delete()
        except ProtectedError:
            # `Perfil.rol` es PROTECT. El conteo de arriba solo mira MI
            # empresa (no se puede revelar el uso que le den otras), asi que
            # todavia puede quedar algun perfil ajeno colgando del rol. Se
            # responde 400 sin decir de quien es: un 500 no aporta nada y el
            # dato de otro tenant no debe salir de aqui.
            return Response({"codigo": "ROL_EN_USO",
                             "detalle": "El rol sigue asignado a alguna cuenta "
                                        "y no se puede eliminar."},
                            status=status.HTTP_400_BAD_REQUEST)
        ActividadUsuario.registrar(request.user, "ROL_ELIMINADO", nombre)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RolClonarView(APIView):
    """POST duplica un rol como plantilla: mismos permisos, nombre temporal."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def post(self, request, id):
        empresa = request.user.perfil.empresa
        origen = RolDetalleView.obtener_rol(empresa, id)
        if origen is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        base = f"{origen.nombre} (COPIA)"
        nombre = base
        contador = 2
        visibles = roles_visibles(empresa)
        while visibles.filter(nombre__iexact=nombre).exists():
            nombre = f"{base} {contador}"
            contador += 1

        with transaction.atomic():
            clon = Rol.objects.create(nombre=nombre, empresa=empresa,
                                      descripcion=f"Copia de {origen.nombre}. "
                                                  "Renombrala y ajusta sus permisos.")
            codigos = list(origen.rol_permisos.values_list("permiso__codigo", flat=True))
            asignar_permisos(clon, codigos)

        ActividadUsuario.registrar(request.user, "ROL_CLONADO",
                                   f"{origen.nombre} -> {clon.nombre} "
                                   f"({len(codigos)} permisos)")
        return Response(RolLecturaSerializer(clon, context={"empresa": empresa}).data,
                        status=status.HTTP_201_CREATED)


class PermisosCatalogoView(APIView):
    """GET catalogo completo de permisos disponibles para asignar."""
    permission_classes = [IsAuthenticated, EsAdministrador]

    def get(self, request):
        datos = [{"codigo": p.codigo, "descripcion": p.descripcion}
                 for p in Permiso.objects.order_by("codigo")]
        return Response({"resultados": datos, "total": len(datos)})
