import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models.functions import Lower
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .identidad import por_correo
from .intentos import contador_para
from .models import ActividadUsuario, Perfil, RolPermiso, TokenRecuperacion
from .serializers import (
    CambiarPasswordSerializer, ConfirmarRecuperacionSerializer, LoginSerializer,
    RegistroCompradorSerializer, RegistroSerializer,
    SolicitarRecuperacionSerializer,
)

logger = logging.getLogger(__name__)

Usuario = get_user_model()


# Cuerpo unico del 401: mismo codigo y mismo texto exista o no el correo, y
# sin `intentos_restantes` (revelaba que la cuenta era real y cuanto faltaba
# para bloquearla). Cualquier dato extra aqui vuelve a abrir la enumeracion.
CREDENCIALES_INVALIDAS = {
    "codigo": "CREDENCIALES_INVALIDAS",
    "detalle": "Correo o contrasena incorrectos.",
}
AVISO_ULTIMO_INTENTO = ("Si el siguiente intento tambien falla, el acceso se "
                        "bloqueara temporalmente.")


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        entrada = LoginSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa email y contrasena.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)
        email = entrada.validated_data["email"]
        password = entrada.validated_data["password"]

        # Identidad candidata resuelta UNA sola vez y sin ambiguedad: por
        # `auth_user` (LOWER(email) con indice UNIQUE funcional), no por
        # `Perfil`. Ordenar por pk deja el resultado determinista tambien en
        # una base heredada a la que aun no se le haya aplicado la
        # verificacion de duplicados.
        # Se compara con `Lower(...)` y no con `iexact` porque en MySQL
        # `iexact` se traduce a un LIKE cuya sensibilidad depende de la
        # collation del despliegue; `LOWER()` da el mismo resultado en
        # cualquier collation y ademas es la expresion que indexa la
        # migracion 0012, asi que la busqueda sigue usando indice.
        # El select_related trae perfil, empresa y rol en la misma consulta:
        # evita las 3 consultas extra que costaba armar el contexto al final.
        candidato = (Usuario.objects
                     .alias(correo=Lower("email"))
                     .filter(correo=email)
                     .select_related("perfil__empresa", "perfil__rol")
                     .order_by("pk").first())
        contador = contador_para(candidato, email, request)

        # El bloqueo se responde igual haya cuenta o no (el contador anonimo
        # replica la ventana), y sin llegar a verificar la contrasena: no
        # introduce diferencia de tiempo porque ninguna de las dos ramas
        # calcula el hash.
        if contador.esta_bloqueado():
            if candidato is not None:
                ActividadUsuario.registrar(candidato, "LOGIN_BLOQUEADO",
                                           f"Cuenta bloqueada: {email}")
            return self._respuesta_bloqueo(contador)

        # `authenticate` calcula el hash de la contrasena tanto si el usuario
        # existe como si no (ModelBackend hace un hash en vacio), asi que el
        # coste -- y el tiempo de respuesta -- es el mismo en ambos casos.
        # Devuelve None tambien para cuentas inactivas: esas caen en el 401
        # generico a proposito, para no delatar que la cuenta existe.
        usuario = authenticate(request, username=email, password=password)

        if usuario is None:
            contador.registrar_fallo()
            ActividadUsuario.registrar(candidato, "LOGIN_FALLIDO",
                                       f"Credenciales invalidas para {email}")
            if contador.esta_bloqueado():
                ActividadUsuario.registrar(candidato, "CUENTA_BLOQUEADA",
                                           f"Se superaron los intentos: {email}")
                return self._respuesta_bloqueo(contador)
            cuerpo = dict(CREDENCIALES_INVALIDAS)
            if contador.intentos_restantes() == 1:
                cuerpo["aviso"] = AVISO_ULTIMO_INTENTO
            return Response(cuerpo, status=status.HTTP_401_UNAUTHORIZED)

        # A partir de aqui la contrasena ya esta probada, asi que distinguir
        # los motivos de rechazo no sirve para enumerar nada.
        # El perfil sale del OneToOne del usuario AUTENTICADO: el contexto
        # (empresa, rol, permisos) no puede venir de otra cuenta.
        perfil = self._perfil_de(usuario, candidato)
        if perfil is None or perfil.deleted_at:
            return Response({"codigo": "USUARIO_INACTIVO"}, status=status.HTTP_403_FORBIDDEN)

        if perfil.empresa_id and not perfil.empresa.activa:
            ActividadUsuario.registrar(usuario, "LOGIN_EMPRESA_INACTIVA", email)
            return Response({"codigo": "EMPRESA_INACTIVA"}, status=status.HTTP_403_FORBIDDEN)

        contador.reiniciar()
        refresh = RefreshToken.for_user(usuario)
        nombre = (usuario.get_full_name() or usuario.username).strip()
        ActividadUsuario.registrar(usuario, "LOGIN_EXITOSO", email)

        return Response({
            "access": str(refresh.access_token), "refresh": str(refresh),
            # `usuario.id` es el id de auth_user (el sujeto del token). El id
            # del perfil viaja aparte en `perfil_id`: antes se devolvia el del
            # perfil bajo la clave `id` y el frontend creia tener el del User.
            "usuario": {"id": str(usuario.id), "perfil_id": str(perfil.id),
                        "email": usuario.email, "nombre": nombre,
                        "rol": perfil.nombre_rol,
                        "empresa": str(perfil.empresa_id) if perfil.empresa_id else None,
                        "empresa_nombre": perfil.empresa.nombre if perfil.empresa_id else None,
                        "debe_cambiar_password": perfil.debe_cambiar_password},
        })

    @staticmethod
    def _respuesta_bloqueo(contador):
        return Response({"codigo": "CUENTA_BLOQUEADA",
                         "desbloqueo_en": contador.desbloqueo_en},
                        status=status.HTTP_423_LOCKED)

    @staticmethod
    def _perfil_de(usuario, candidato):
        """Perfil del usuario autenticado, reutilizando el select_related ya
        cargado cuando `authenticate` devolvio esa misma fila (caso normal).
        Asi el login no repite las consultas de perfil, empresa y rol."""
        if candidato is not None and candidato.pk == usuario.pk:
            return getattr(candidato, "perfil", None)
        return getattr(usuario, "perfil", None)


class MeView(APIView):
    """Fuente unica de permisos del frontend (fase Empleados): el menu y los
    guards se arman a partir de `permisos`, no del nombre del rol."""

    def get(self, request):
        # Una sola consulta para perfil + empresa + rol (antes eran tres:
        # el perfil por el OneToOne y luego `perfil.rol` y `perfil.empresa`
        # al serializar).
        perfil = (Perfil.objects.filter(usuario=request.user)
                  .select_related("empresa", "rol").first())
        if perfil is None:
            return Response({"codigo": "SIN_PERFIL"}, status=status.HTTP_403_FORBIDDEN)

        usuario = request.user
        nombre = (usuario.get_full_name() or usuario.username).strip()
        permisos = list(
            RolPermiso.objects.filter(rol_id=perfil.rol_id)
            .values_list("permiso__codigo", flat=True)
        )
        return Response({
            "id": str(usuario.id), "perfil_id": str(perfil.id),
            "email": usuario.email, "nombre": nombre,
            "rol": perfil.nombre_rol,
            "empresa": str(perfil.empresa_id) if perfil.empresa_id else None,
            "empresa_nombre": perfil.empresa.nombre if perfil.empresa_id else None,
            "permisos": permisos,
            "debe_cambiar_password": perfil.debe_cambiar_password,
        })


class CambiarPasswordView(APIView):
    """Cambio de contrasena propio. Ruta exenta de CambioPasswordMiddleware:
    es la unica escritura permitida mientras debe_cambiar_password=True."""

    def post(self, request):
        entrada = CambiarPasswordSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos de la contrasena.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user
        if not usuario.check_password(entrada.validated_data["password_actual"]):
            return Response({"codigo": "PASSWORD_ACTUAL_INCORRECTA"},
                            status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(entrada.validated_data["password_nueva"])
        usuario.save(update_fields=["password"])

        perfil = getattr(usuario, "perfil", None)
        if perfil and perfil.debe_cambiar_password:
            perfil.debe_cambiar_password = False
            perfil.save(update_fields=["debe_cambiar_password"])

        ActividadUsuario.registrar(usuario, "PASSWORD_CAMBIADA", usuario.email)
        return Response(status=status.HTTP_200_OK)


class TokenRefreshThrottleView(TokenRefreshView):
    """Refresh con limite por IP (scope `auth_refresh`). Prevencion de fuerza
    bruta sobre tokens de sesion desde una misma IP."""

    throttle_scope = 'auth_refresh'


class RegistroEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'auth_registro'

    def post(self, request):
        entrada = RegistroSerializer(data=request.data)
        if not entrada.is_valid():
            return Response({"codigo": "DATOS_INVALIDOS", "detalle": "Revisa los datos del formulario.",
                             "errores": entrada.errors}, status=status.HTTP_400_BAD_REQUEST)
        usuario = entrada.save()
        ActividadUsuario.registrar(usuario, "REGISTRO_EMPRESA", usuario.email)
        return Response(status=status.HTTP_201_CREATED)


class RegistroCompradorView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'auth_registro'

    def post(self, request):
        entrada = RegistroCompradorSerializer(data=request.data)
        if not entrada.is_valid():
            return Response({"codigo": "DATOS_INVALIDOS", "detalle": "Revisa los datos del formulario.",
                             "errores": entrada.errors}, status=status.HTTP_400_BAD_REQUEST)
        usuario = entrada.save()
        ActividadUsuario.registrar(usuario, "REGISTRO_COMPRADOR", usuario.email)
        return Response(status=status.HTTP_201_CREATED)


class EmailDisponibleView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        email = (request.query_params.get("email") or "").strip().lower()
        if not email:
            return Response({"disponible": False}, status=status.HTTP_400_BAD_REQUEST)
        existe = por_correo(Usuario, email).exists()
        return Response({"disponible": not existe})


class SolicitarRecuperacionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'auth_recuperacion'

    def post(self, request):
        entrada = SolicitarRecuperacionSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(
                {"codigo": "DATOS_INVALIDOS",
                 "detalle": "Revisa los datos.",
                 "errores": entrada.errors},
                status=status.HTTP_400_BAD_REQUEST)
        email = entrada.validated_data["email"]

        perfil = (Perfil.objects
                  .filter(usuario__in=por_correo(Usuario, email))
                  .select_related("usuario").first())
        if perfil and perfil.usuario.is_active:
            token = TokenRecuperacion.emitir(perfil, minutos=30)
            enlace = f"{settings.FRONTEND_URL}/restablecer?token={token}"
            mensaje_texto = (
                "Hola.\n\n"
                "Recibimos una solicitud para restablecer tu contrasena de InterSoft.\n\n"
                f"Abre este enlace (vence en 30 minutos):\n{enlace}\n\n"
                "Si no fuiste tu, ignora este correo."
            )
            mensaje_html = (
                "<div style='font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:auto'>"
                "<h2 style='color:#1f2937'>InterSoft</h2>"
                "<p>Hola,</p>"
                "<p>Recibimos una solicitud para restablecer tu contrasena.</p>"
                "<p>Haz clic en el boton para crear una nueva (vence en 30 minutos):</p>"
                "<p><a href='" + enlace + "' "
                "style='display:inline-block;background-color:#2563eb;color:#ffffff;"
                "padding:12px 22px;border-radius:6px;text-decoration:none;font-weight:bold'>"
                "Restablecer contrasena</a></p>"
                "<p style='color:#6b7280;font-size:12px'>"
                "Si el boton no funciona, copia este enlace: <a href='" + enlace + "'>" + enlace + "</a></p>"
                "<hr style='margin-top:28px;border:none;border-top:1px solid #e5e7eb'>"
                "<p style='color:#9ca3af;font-size:12px'>Si no solicitaste este cambio, "
                "ignora este correo.</p>"
                "</div>"
            )
            try:
                correo = EmailMultiAlternatives(
                    subject="Restablece tu contrasena de InterSoft",
                    body=mensaje_texto,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[perfil.usuario.email],
                )
                correo.attach_alternative(mensaje_html, "text/html")
                # En desarrollo (consola) no se lanza; en produccion (SMTP)
                # no se ocultan errores reales de envio.
                enviado = correo.send(fail_silently=settings.DEBUG)
            except Exception as exc:  # noqa: BLE001
                # No revelamos al usuario el fallo (anti-enumeracion), pero
                # queda registrado internamente para operacion.
                logger.warning(
                    "Fallo el envio de recuperacion para %s: %s", email, exc)
                return Response(status=status.HTTP_200_OK)
            ActividadUsuario.registrar(
                perfil.usuario, "SOLICITUD_RECUPERACION",
                f"Email enviado: {email}" if enviado else f"Email no entregado: {email}")
        return Response(status=status.HTTP_200_OK)   # SIEMPRE 200


class ConfirmarRecuperacionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'auth_recuperacion'

    def post(self, request):
        entrada = ConfirmarRecuperacionSerializer(data=request.data)
        if not entrada.is_valid():
            return Response({"codigo": "DATOS_INVALIDOS", "detalle": "La contrasena no cumple los requisitos."},
                            status=status.HTTP_400_BAD_REQUEST)

        token_plano = entrada.validated_data["token"]
        registro = TokenRecuperacion.objects.filter(
            token_hash=TokenRecuperacion.calcular_hash(token_plano)
        ).select_related("perfil__usuario").first()

        if registro is None or not registro.es_valido():
            return Response({"codigo": "TOKEN_INVALIDO", "detalle": "El enlace vencio o ya fue usado."},
                            status=status.HTTP_400_BAD_REQUEST)

        usuario = registro.perfil.usuario
        usuario.set_password(entrada.validated_data["password"])
        usuario.save(update_fields=["password"])
        registro.usado = True
        registro.save(update_fields=["usado"])
        registro.perfil.reiniciar_intentos()
        ActividadUsuario.registrar(usuario, "PASSWORD_RESTABLECIDO", usuario.email)
        return Response(status=status.HTTP_200_OK)
