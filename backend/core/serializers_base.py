"""Piezas compartidas entre los serializers del panel y los de la tienda.

`imagen` se resolvia de forma distinta en cada sitio: el `ImageField` de DRF
devuelve una URL absoluta solo si el `request` esta en el contexto del
serializer. El catalogo publico lo pasaba y el panel no, asi que
`/api/tienda/catalogo/` devolvia `http://host/media/...` y `/api/productos/`
devolvia `/media/...`. En el panel, servido desde otro origen que la API en
desarrollo, esa ruta relativa apunta al servidor de Angular y la imagen sale
rota.

Este mixin construye la URL absoluta de forma explicita para que el
comportamiento no dependa de si alguien se acordo de pasar el `request`, y
deja claro en el codigo que el contrato es "URL absoluta".
"""

from rest_framework import serializers


class ImagenAbsolutaMixin(serializers.Serializer):
    """Expone `imagen` como URL absoluta (o `None` si no hay archivo).

    Si el `request` no esta en el contexto se devuelve la ruta relativa en vez
    de fallar -- es lo mejor que se puede hacer sin saber el host -- pero las
    vistas deben pasarlo siempre; hay pruebas que fijan que la URL empiece por
    `http`.
    """

    imagen = serializers.SerializerMethodField()

    def get_imagen(self, obj) -> str | None:
        archivo = getattr(obj, "imagen", None)
        if not archivo:
            return None
        url = archivo.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request is not None else url


def url_absoluta_de_imagen(obj, request) -> str | None:
    """Misma regla que el mixin, para las vistas que arman dicts a mano
    (p. ej. el listado de inventario) en vez de usar un serializer."""
    archivo = getattr(obj, "imagen", None)
    if not archivo:
        return None
    return request.build_absolute_uri(archivo.url) if request is not None else archivo.url
