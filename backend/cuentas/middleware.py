"""Auditoria automatica (fase 1): toda peticion de escritura autenticada
que termine bien queda registrada en actividad_usuario.

Las acciones de autenticacion (login, recuperacion) se registran aparte,
directo en las vistas, porque ahi el request.user puede ser anonimo.
"""

from django.http import JsonResponse

METODOS_ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}
PREFIJOS_IGNORADOS = ("/static/", "/media/")


class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self.registrar(request, response)
        except Exception:  # la auditoria jamas debe romper la respuesta
            import logging
            logging.getLogger(__name__).exception("Fallo al registrar actividad")
        return response

    def registrar(self, request, response):
        if request.method not in METODOS_ESCRITURA:
            return
        if not 200 <= response.status_code < 400:
            return
        if any(request.path.startswith(p) for p in PREFIJOS_IGNORADOS):
            return

        usuario = getattr(request, "user", None)
        if usuario is None or not usuario.is_authenticated:
            return

        from .models import ActividadUsuario
        match = getattr(request, "resolver_match", None)
        vista = getattr(match, "view_name", None) or request.path
        ActividadUsuario.registrar(
            usuario=usuario,
            accion=f"{vista} [{request.method}]",
            detalle=request.path,
        )


class CambioPasswordMiddleware:
    """Fase Empleados: si el Perfil tiene debe_cambiar_password=True, bloquea
    toda la API (403 CAMBIO_PASSWORD_REQUERIDO) salvo login, /auth/me/ y el
    endpoint de cambio de contrasena.

    Corre ANTES de la vista (a diferencia de AuditoriaMiddleware). request.user
    todavia no existe para peticiones JWT en este punto -- lo que rellena
    AuthenticationMiddleware es la sesion, no el token -- asi que el token se
    decodifica aqui mismo con JWTAuthentication.
    """

    RUTAS_EXENTAS = (
        "/api/auth/login/",
        "/api/auth/me/",
        "/api/auth/cambiar-password/",
        "/static/",
        "/media/",
        "/admin/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/") or \
           any(request.path.startswith(p) for p in self.RUTAS_EXENTAS):
            return self.get_response(request)

        perfil = self._perfil_del_token(request)
        if perfil is not None and perfil.debe_cambiar_password:
            return JsonResponse(
                {"error": "CAMBIO_PASSWORD_REQUERIDO",
                 "detalle": "Debe cambiar su contrasena antes de continuar."},
                status=403,
            )
        return self.get_response(request)

    @staticmethod
    def _perfil_del_token(request):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        try:
            resultado = JWTAuthentication().authenticate(request)
        except Exception:
            return None
        if not resultado:
            return None
        usuario, _token = resultado
        return getattr(usuario, "perfil", None)
