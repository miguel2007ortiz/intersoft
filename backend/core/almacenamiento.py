"""Almacenamiento de documentos que NO deben servirse como estaticos.

Las facturas electronicas, las notas credito y los recibos vivian en
`MEDIA_ROOT`, junto a las imagenes de producto. Eso los dejaba al alcance de
cualquiera: `/media/` lo sirve nginx (y `static()` en desarrollo) sin pasar por
la autenticacion de Django, y los nombres son adivinables --
`FE-<numero_factura>.pdf`.

Bloquear esas rutas en nginx tapaba el agujero, pero dependia de que nadie
volviera a abrirlo al tocar la configuracion. Guardarlos fuera de `MEDIA_ROOT`
lo cierra por construccion: aunque alguien exponga `/media/` entero, estos
archivos no estan ahi.

Se descargan por la API (`/api/facturacion/<id>/archivo/<tipo>/` y
`/api/ventas/<id>/recibo/`), que exige sesion y filtra por empresa.
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class AlmacenamientoPrivado(FileSystemStorage):
    """Guarda bajo `DOCUMENTOS_ROOT`, fuera de `MEDIA_ROOT`, y sin URL.

    `.url` lanza `ValueError`: si alguien intenta publicar el enlace de un
    documento, falla en el sitio en vez de devolver una ruta publica en
    silencio. Pasar `base_url=None` no basta -- `FileSystemStorage.base_url`
    cae a `MEDIA_URL` cuando es `None`, y devolveria justo la ruta publica que
    esto quiere evitar --, asi que se sobreescribe `url()`.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("location", settings.DOCUMENTOS_ROOT)
        super().__init__(**kwargs)

    def url(self, name):
        raise ValueError(
            "Los comprobantes no se sirven por URL. Usa el endpoint de "
            "descarga, que exige sesion y filtra por empresa.")

    def deconstruct(self):
        """Se serializa sin argumentos para que la ruta concreta no quede
        escrita en una migracion: cada entorno la toma de su settings."""
        return ("core.almacenamiento.AlmacenamientoPrivado", [], {})


documentos_privados = AlmacenamientoPrivado()
