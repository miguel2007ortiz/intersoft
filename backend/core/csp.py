"""Cabecera CSP (Content Security Policy) — defensa en profundidad.

La pagina HTML (SPA Angular) la sirve nginx, que es quien emite la cabecera
realmente importante (ver `frontend/nginx.conf` y `docs/DESPLIEGUE.md`).
Este middleware la repite en las respuestas del backend (JSON, media PDF/XML,
fallback de index) para que ninguna respuesta viaje sin politica aunque alguien
sirva algo via Django; sobre JSON no tiene efecto, pero asi el nginx que no la
configure y un despliegue con fallback no quedan desprotegidos.

Directivas elegidas para la SPA (todo mismo-origen salvo el API en despliegue
separado, que se abre via `connect-src`):
  - script-src 'self'      : sin eval; Angular solo usa bundles con hash.
  - style-src 'unsafe-inline': Angular inyecta <style> en runtime (emulacion
    de estilos encapsulados); sin esto la SPA se rompe.
  - img-src data:/blob:    : preview de imagen al subir producto
    (URL.createObjectURL) y una eventual portada en data:.
  - frame-ancestors 'none' : refuerza X-FRAME_OPTIONS=DENY contra clickjacking.
  - base-uri 'self'        : impide inyeccion de <base>.
"""

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "frame-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'"
)


def csp_middleware(get_response):
    """Agrega la cabecera CSP a toda respuesta si no viene ya definida."""
    def procesar(request):
        response = get_response(request)
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = CONTENT_SECURITY_POLICY
        return response
    return procesar