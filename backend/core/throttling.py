"""Throttling por IP para endpoints sensibles (RIESGOS.md, pendiente 1).

Complementa el bloqueo por cuenta del login: limita por IP el propio login,
el refresh, la recuperacion de contrasena y la creacion de cuentas, que no
tienen identidad de usuario previa (o que no deben depender de ella).

Como se identifica al cliente
-----------------------------
La identificacion la resuelve `BaseThrottle.get_ident` de DRF a partir de
`NUM_PROXIES`, que se configura por entorno (ver `.env.example`):

  - `NUM_PROXIES=0` (local, valor por omision): se usa `REMOTE_ADDR` y se
    IGNORA `X-Forwarded-For`. Sin proxy delante, esa cabecera la pone el
    cliente, asi que confiar en ella deja reiniciar el contador a voluntad.
  - `NUM_PROXIES=n` (despliegue detras de n proxies): se toma el elemento
    `-n` de `X-Forwarded-For`, es decir la IP que anadio el proxy en el que
    si se confia. Un atacante puede prefijar valores falsos, pero no puede
    alterar los ultimos n, que son los que escriben los proxies propios.

Esta clase ya NO sobrescribe `get_ident`: lo hacia leyendo siempre el ultimo
elemento de `X-Forwarded-For`, lo que equivalia a `NUM_PROXIES=1` fijo y, sin
proxy delante, hacia el limite evadible con una cabecera inventada.

Sin `throttle_scope` en la vista no limita (mismo comportamiento que el
`ScopedRateThrottle` de DRF).
"""
from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle


class IPScopedRateThrottle(ScopedRateThrottle):
    """`ScopedRateThrottle` de DRF con las tasas leidas en cada peticion.

    DRF captura `DEFAULT_THROTTLE_RATES` como atributo de clase al importar,
    lo que hace inutil `override_settings(REST_FRAMEWORK=...)` en los tests.
    Leerlas aqui mantiene las pruebas de limites honestas.
    """

    def get_rate(self):
        try:
            return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
        except KeyError:
            from rest_framework.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "No default throttle rate set for '%s' scope" % self.scope)
