import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import EmailMultiAlternatives
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import ActividadUsuario, Perfil, RolPermiso, TokenRecuperacion
from .serializers import (
    CambiarPasswordSerializer, ConfirmarRecuperacionSerializer, LoginSerializer,
    RegistroCompradorSerializer, RegistroSerializer,
    SolicitarRecuperacionSerializer,
)

logger = logging.getLogger(__name__)

Usuario = get_user_model()


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

        # Identidad UNICA: el perfil de la respuesta sale SIEMPRE del usuario
        # autenticado (usuario.perfil), no de la busqueda preliminar por email.
        # La busqueda previa solo sirve para los controles anteriores al
        # authenticate (bloqueo / cuenta inactiva); nunca para construir la
        # respuesta, porque dos cuentas distintas podrian compartir email y
        # el perfil de la respuesta debe ser el de quien realmente entro.
        perfil_pre = (Perfil.objects.filter(usuario__email__iexact=email)
                      .select_related("usuario", "rol", "empresa")
                      .order_by("usuario__id").first())

        if perfil_pre and perfil_pre.esta_bloqueado():
            ActividadUsuario.registrar(perfil_pre.usuario, "LOGIN_BLOQUEADO",
                                       f"Cuenta bloqueada: {email}")
            return Response({"codigo": "CUENTA_BLOQUEADA", "desbloqueo_en": perfil_pre.fecha_desbloqueo},
                            status=status.HTTP_423_LOCKED)

        # La cuenta desactivada o borrada no debe consumir intentos ni
        # recibir un mensaje de credenciales invalidas.
        if perfil_pre and (not perfil_pre.usuario.is_active or perfil_pre.deleted_at):
            return Response({"codigo": "USUARIO_INACTIVO"}, status=status.HTTP_403_FORBIDDEN)

        usuario = authenticate(request, username=email, password=password)

        if usuario is None:
            if perfil_pre:
                perfil_pre.registrar_intento_fallido()
                ActividadUsuario.registrar(perfil_pre.usuario, "LOGIN_FALLIDO",
                                           f"Contrasena invalida para {email}")
                if perfil_pre.esta_bloqueado():
                    ActividadUsuario.registrar(perfil_pre.usuario, "CUENTA_BLOQUEADA",
                                               f"Se superaron los intentos: {email}")
                    return Response({"codigo": "CUENTA_BLOQUEADA", "desbloqueo_en": perfil_pre.fecha_desbloqueo},
                                    status=status.HTTP_423_LOCKED)
            else:
                ActividadUsuario.registrar(None, "LOGIN_FALLIDO", f"Correo inexistente: {email}")
            # Respuesta identica exista o no el correo: no se revela cuantos
            # intentos quedan (oraculo de enumeracion de cuentas, BUG-19 QA).
            return Response({"codigo": "CREDENCIALES_INVALIDAS"},
                            status=status.HTTP_401_UNAUTHORIZED)

        if not usuario.is_active:
            return Response({"codigo": "USUARIO_INACTIVO"}, status=status.HTTP_403_FORBIDDEN)

        # Identidad real: el perfil del usuario que se acaba de autenticar.
        # Si el prelookup por email ya corresponde al mismo usuario, se
        # reutiliza (ya viene con select_related); en el raro caso de correos
        # repetidos se consulta por usuario, que es la fuente unica y real.
        if perfil_pre and perfil_pre.usuario_id == usuario.id:
            perfil = perfil_pre
        else:
            perfil = (Perfil.objects.select_related("empresa", "rol")
                      .filter(usuario=usuario, deleted_at__isnull=True).first())
        if perfil is None:
            return Response({"codigo": "USUARIO_INACTIVO"}, status=status.HTTP_403_FORBIDDEN)

        if perfil.empresa_id and not perfil.empresa.activa:
            ActividadUsuario.registrar(usuario, "LOGIN_EMPRESA_INACTIVA", email)
            return Response({"codigo": "EMPRESA_INACTIVA"}, status=status.HTTP_403_FORBIDDEN)

        perfil.reiniciar_intentos()
        refresh = RefreshToken.for_user(usuario)
        nombre = (usuario.get_full_name() or usuario.username).strip()
        ActividadUsuario.registrar(usuario, "LOGIN_EXITOSO", email)

        return Response({
            "access": str(refresh.access_token), "refresh": str(refresh),
            "usuario": {"id": str(perfil.id), "email": usuario.email, "nombre": nombre,
                        "rol": perfil.nombre_rol,
                        "empresa": str(perfil.empresa_id) if perfil.empresa_id else None,
                        "empresa_nombre": perfil.empresa.nombre if perfil.empresa_id else None,
                        "debe_cambiar_password": perfil.debe_cambiar_password},
        })


class MeView(APIView):
    """Fuente unica de permisos del frontend (fase Empleados): el menu y los
    guards se arman a partir de `permisos`, no del nombre del rol."""

    def get(self, request):
        perfil = getattr(request.user, "perfil", None)
        if perfil is None:
            return Response({"codigo": "SIN_PERFIL"}, status=status.HTTP_403_FORBIDDEN)

        usuario = perfil.usuario
        nombre = (usuario.get_full_name() or usuario.username).strip()
        permisos = list(
            RolPermiso.objects.filter(rol=perfil.rol)
            .values_list("permiso__codigo", flat=True)
        )
        return Response({
            "id": str(perfil.id), "email": usuario.email, "nombre": nombre,
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
        existe = Usuario.objects.filter(email__iexact=email).exists()
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

        perfil = (Perfil.objects.filter(usuario__email__iexact=email)
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
