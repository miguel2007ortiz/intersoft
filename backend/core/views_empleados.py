"""API del modulo Empleados (personal interno): CRUD de Perfil+User con
datos laborales, separado de /api/seguridad/usuarios/ (fase 2, sigue intacto).

Reglas de negocio:
- solo quien tiene el permiso fino correspondiente puede crear/leer/editar/
  desactivar personal (TienePermiso, no el nombre del rol);
- documento (tipo+numero) unico por empresa, incluidos los inactivos;
- no puede quedar la empresa sin ningun ADMINISTRADOR activo;
- nadie puede desactivarse a si mismo;
- la contrasena temporal la genera el servidor si no la manda el
  ADMINISTRADOR, y se devuelve una sola vez en la respuesta de creacion.
Toda accion queda auditada en actividad_usuario."""

import secrets
import string

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import ActividadUsuario, Perfil
from cuentas.permissions import TienePermiso

from .serializers_empleados import (
    EmpleadoDetalleSerializer, EmpleadoEscrituraSerializer, EmpleadoLecturaSerializer,
)


def respuesta_datos_invalidos(errores):
    return Response({"codigo": "DATOS_INVALIDOS",
                     "detalle": "Revisa los datos del formulario.",
                     "errores": errores}, status=status.HTTP_400_BAD_REQUEST)


def generar_password_temporal() -> str:
    """Password aleatoria que siempre cumple validar_fuerza_password
    (>=8, mayuscula, minuscula, numero)."""
    obligatorios = [secrets.choice(string.ascii_uppercase),
                    secrets.choice(string.ascii_lowercase),
                    secrets.choice(string.digits)]
    resto = [secrets.choice(string.ascii_letters + string.digits) for _ in range(9)]
    caracteres = obligatorios + resto
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)


def perfiles_de_empresa(empresa):
    return (Perfil.objects.filter(empresa=empresa)
            .select_related("usuario", "rol"))


def hay_otro_admin_activo(empresa, excluir_id) -> bool:
    return (Perfil.objects.filter(empresa=empresa, rol__nombre="ADMINISTRADOR",
                                  deleted_at__isnull=True, usuario__is_active=True)
            .exclude(pk=excluir_id).exists())


class EmpleadosView(APIView):
    """GET lista (busqueda, filtro de estado y paginacion) / POST crea empleado."""
    POR_PAGINA = 25

    def get_permissions(self):
        codigo = "empleado.crear" if self.request.method == "POST" else "empleado.leer"
        return [IsAuthenticated(), TienePermiso(codigo)()]

    def get(self, request):
        perfiles = perfiles_de_empresa(request.user.perfil.empresa)

        estado = request.query_params.get("estado", "activos")
        if estado == "activos":
            perfiles = perfiles.filter(deleted_at__isnull=True, usuario__is_active=True)
        elif estado == "inactivos":
            perfiles = perfiles.filter(Q(deleted_at__isnull=False) | Q(usuario__is_active=False))
        # estado == "todos": sin filtro adicional

        busqueda = request.query_params.get("busqueda", "").strip()
        if busqueda:
            perfiles = perfiles.filter(
                Q(usuario__first_name__icontains=busqueda)
                | Q(usuario__last_name__icontains=busqueda)
                | Q(usuario__email__icontains=busqueda)
                | Q(numero_documento__icontains=busqueda))

        perfiles = perfiles.order_by("usuario__first_name", "usuario__last_name")
        total = perfiles.count()
        try:
            pagina = max(int(request.query_params.get("pagina", 1)), 1)
        except (TypeError, ValueError):
            pagina = 1
        inicio = (pagina - 1) * self.POR_PAGINA
        datos = EmpleadoLecturaSerializer(
            perfiles[inicio:inicio + self.POR_PAGINA], many=True).data
        return Response({
            "resultados": datos,
            "total": total,
            "pagina": pagina,
            "por_pagina": self.POR_PAGINA,
            "total_paginas": max((total + self.POR_PAGINA - 1) // self.POR_PAGINA, 1),
        })

    def post(self, request):
        entrada_datos = request.data
        password_generada = None
        if not entrada_datos.get("password"):
            password_generada = generar_password_temporal()
            entrada_datos = {**request.data, "password": password_generada}

        entrada = EmpleadoEscrituraSerializer(
            data=entrada_datos, context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidos(entrada.errors)

        try:
            with transaction.atomic():
                perfil = entrada.save()
        except IntegrityError:
            return Response({
                "codigo": "DOCUMENTO_DUPLICADO",
                "detalle": "Ese documento ya fue registrado (posible doble envio). "
                           "Actualiza el listado antes de reintentar.",
            }, status=status.HTTP_400_BAD_REQUEST)

        ActividadUsuario.registrar(request.user, "EMPLEADO_CREADO",
                                   f"{perfil.usuario.email} ({perfil.rol.nombre})")
        respuesta = EmpleadoDetalleSerializer(
            perfil, context={"empresa": request.user.perfil.empresa}).data
        if password_generada:
            # RN-09: no hay canal de notificacion configurado -> se muestra
            # una unica vez en la respuesta, el frontend la despliega en un
            # modal y no vuelve a estar disponible despues de esto.
            respuesta["password_temporal"] = password_generada
        return Response(respuesta, status=status.HTTP_201_CREATED)


class EmpleadoDetalleView(APIView):
    """GET (incluye ultimas 5 ventas) / PUT-PATCH / DELETE (borrado logico)."""

    def get_permissions(self):
        codigo = {"GET": "empleado.leer", "PUT": "empleado.actualizar",
                  "PATCH": "empleado.actualizar", "DELETE": "empleado.desactivar"}[self.request.method]
        return [IsAuthenticated(), TienePermiso(codigo)()]

    def obtener_perfil(self, request, id):
        return perfiles_de_empresa(request.user.perfil.empresa).filter(id=id).first()

    def get(self, request, id):
        perfil = self.obtener_perfil(request, id)
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(EmpleadoDetalleSerializer(
            perfil, context={"empresa": request.user.perfil.empresa}).data)

    def put(self, request, id):
        return self.editar(request, id, parcial=False)

    def patch(self, request, id):
        return self.editar(request, id, parcial=True)

    def editar(self, request, id, parcial: bool):
        perfil = self.obtener_perfil(request, id)
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        nuevo_rol = (request.data.get("rol") or "").strip().upper()
        if nuevo_rol and nuevo_rol != perfil.rol.nombre and perfil.rol.nombre == "ADMINISTRADOR" \
                and not hay_otro_admin_activo(request.user.perfil.empresa, perfil.id):
            return Response({"codigo": "UNICO_ADMINISTRADOR",
                             "detalle": "Debe existir al menos un ADMINISTRADOR activo "
                                        "en la empresa; asigna el rol a otra cuenta primero."},
                            status=status.HTTP_400_BAD_REQUEST)

        entrada = EmpleadoEscrituraSerializer(
            perfil, data=request.data, partial=parcial,
            context={"empresa": request.user.perfil.empresa})
        if not entrada.is_valid():
            return respuesta_datos_invalidos(entrada.errors)

        try:
            with transaction.atomic():
                perfil = entrada.save()
        except IntegrityError:
            return Response({
                "codigo": "DOCUMENTO_DUPLICADO",
                "detalle": "Ese documento ya fue registrado (posible doble envio). "
                           "Actualiza el listado antes de reintentar.",
            }, status=status.HTTP_400_BAD_REQUEST)

        ActividadUsuario.registrar(request.user, "EMPLEADO_EDITADO", perfil.usuario.email)
        return Response(EmpleadoDetalleSerializer(
            perfil, context={"empresa": request.user.perfil.empresa}).data)

    def delete(self, request, id):
        perfil = self.obtener_perfil(request, id)
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        respuesta_bloqueo = self._bloqueo_desactivar(request, perfil)
        if respuesta_bloqueo is not None:
            return respuesta_bloqueo

        with transaction.atomic():
            perfil.deleted_at = perfil.deleted_at or timezone.now()
            perfil.usuario.is_active = False
            perfil.usuario.save(update_fields=["is_active"])
            perfil.save(update_fields=["deleted_at"])
        ActividadUsuario.registrar(request.user, "EMPLEADO_ELIMINADO", perfil.usuario.email)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _bloqueo_desactivar(request, perfil):
        if perfil.usuario_id == request.user.id:
            return Response({"codigo": "AUTODESACTIVACION_PROHIBIDA",
                             "detalle": "No puedes desactivar tu propia cuenta."},
                            status=status.HTTP_400_BAD_REQUEST)
        if perfil.rol.nombre == "ADMINISTRADOR" and not hay_otro_admin_activo(
                request.user.perfil.empresa, perfil.id):
            return Response({"codigo": "UNICO_ADMINISTRADOR",
                             "detalle": "Debe existir al menos un ADMINISTRADOR activo "
                                        "en la empresa."},
                            status=status.HTTP_400_BAD_REQUEST)
        return None


class EmpleadoEstadoView(APIView):
    """POST desactiva o reactiva un empleado (idempotente: repetir la misma
    accion responde 200, no error)."""
    permission_classes = [IsAuthenticated, TienePermiso("empleado.desactivar")]

    def post(self, request, id, accion):
        perfil = EmpleadoDetalleView().obtener_perfil(request, id)
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if accion not in ("desactivar", "reactivar"):
            return Response(status=status.HTTP_404_NOT_FOUND)

        activo_actual = perfil.deleted_at is None and perfil.usuario.is_active
        deseado_activo = accion == "reactivar"
        if activo_actual == deseado_activo:
            return Response(EmpleadoDetalleSerializer(
                perfil, context={"empresa": request.user.perfil.empresa}).data)

        if not deseado_activo:
            bloqueo = EmpleadoDetalleView._bloqueo_desactivar(request, perfil)
            if bloqueo is not None:
                return bloqueo

        with transaction.atomic():
            if deseado_activo:
                perfil.deleted_at = None
                perfil.usuario.is_active = True
                perfil.usuario.save(update_fields=["is_active"])
                perfil.reiniciar_intentos()
            else:
                perfil.deleted_at = timezone.now()
                perfil.usuario.is_active = False
                perfil.usuario.save(update_fields=["is_active"])
            perfil.save(update_fields=["deleted_at"])
        evento = "EMPLEADO_REACTIVADO" if deseado_activo else "EMPLEADO_DESACTIVADO"
        ActividadUsuario.registrar(request.user, evento, perfil.usuario.email)
        return Response(EmpleadoDetalleSerializer(
            perfil, context={"empresa": request.user.perfil.empresa}).data)


class EmpleadoPasswordView(APIView):
    """POST: el ADMINISTRADOR emite una nueva contrasena temporal para un
    empleado (p. ej. la olvido). Igual que en la creacion, se devuelve una
    sola vez en la respuesta y fuerza el cambio en el siguiente login."""
    permission_classes = [IsAuthenticated, TienePermiso("empleado.actualizar")]

    def post(self, request, id):
        perfil = EmpleadoDetalleView().obtener_perfil(request, id)
        if perfil is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        password_generada = generar_password_temporal()
        with transaction.atomic():
            perfil.usuario.set_password(password_generada)
            perfil.usuario.save(update_fields=["password"])
            perfil.debe_cambiar_password = True
            perfil.save(update_fields=["debe_cambiar_password"])

        ActividadUsuario.registrar(request.user, "EMPLEADO_PASSWORD_REGENERADA",
                                   perfil.usuario.email)
        return Response({"password_temporal": password_generada})
