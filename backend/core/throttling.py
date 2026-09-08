"""Throttling por IP para endpoints sensibles (RIESGOS.md, pendiente 1).

Complementa el bloqueo por cuenta del login: limita por IP peticiones de
refresh, recuperacion de contrasena y creacion de cuentas, que no tienen
identidad de usuario previa. Detras de nginx la IP confiable es la ultima de
la cadena X-Forwarded-For (el proxy anade la IP real del cliente al final),
por eso se lee ese elemento: un atacante no puede reiniciar su contador
falseando la cabecera.

Sin `throttle_scope` en la vista no limita (mismo comportamiento que el
`ScopedRateThrottle` de DRF).
"""
from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle


class IPScopedRateThrottle(ScopedRateThrottle):
    """Igual que el throttle por scope de DRF, pero identifica por IP real del
    cliente en lugar de sesion/cookie (relevante en endpoints AllowAny).

    Sobrescribe `get_rate` para leer `DEFAULT_THROTTLE_RATES` en el momento
    de la peticion: DRF captura ese dict como atributo de clase al importar,
    lo que harta inutil `override_settings(REST_FRAMEWORK=...)` en los tests.
    """

    def get_ident(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            partes = [p.strip() for p in xff.split(',') if p.strip()]
            if partes:
                return partes[-1]
        return request.META.get('REMOTE_ADDR', '')

    def get_rate(self):
        try:
            return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
        except KeyError:
            from rest_framework.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "No default throttle rate set for '%s' scope" % self.scope)