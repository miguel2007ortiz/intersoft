"""Auditoria automatica (fase 1): toda peticion de escritura autenticada
que termine bien queda registrada en actividad_usuario.

Las acciones de autenticacion (login, recuperacion) se registran aparte,
directo en las vistas, porque ahi el request.user puede ser anonimo.
"""

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
