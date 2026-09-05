"""Servicio de camaras (fase 9): resolucion de grabaciones historicas.

Las grabaciones historicas no estan en la base de datos: se buscan en el
servidor de almacenamiento por empresa/camara/fecha/hora y se devuelve la URL
para reproducirlas en el panel.

El camino canónico es:
   {MEDIA_URL}streams/{empresa_id.hex}/{camara_id.hex}/{fecha}/{hora}.mp4

Si la grabación no existe (o en entornos sin servidor de almacenamiento
real) se devuelve `disponible=False` y el panel mostrara un aviso en lugar de
un reproductor roto.
"""

import os
from datetime import datetime

from django.conf import settings


def _ruta_archivo(camara, empresa, fecha, hora):
    nombre = hora.strftime('%H_%M') + '.mp4'
    return os.path.join(
        str(settings.MEDIA_ROOT),
        'streams',
        empresa.id.hex,
        camara.id.hex,
        fecha.strftime('%Y-%m-%d'),
        nombre,
    )


def _resolver_url(camara, empresa, fecha, hora):
    rel = os.path.join(
        'streams', empresa.id.hex, camara.id.hex,
        fecha.strftime('%Y-%m-%d'), hora.strftime('%H_%M') + '.mp4')
    return (settings.MEDIA_URL + rel.replace(os.sep, '/'))


def resolver_grabacion(camara, empresa, fecha_iso, hora_iso):
    """Devuelve dict con la grabacion historica para fecha y hora dadas.

    Si el archivo existe en disco se devuelve su URL; si no, `disponible`
    queda en False. Rango valido: 00:00 a 23:59.
    """
    try:
        fecha = datetime.strptime(fecha_iso, '%Y-%m-%d').date()
        hora = datetime.strptime(hora_iso or '12:00', '%H:%M').time()
    except ValueError:
        return {'disponible': False, 'detalle': 'Fecha u hora invalida.'}

    archivo = _ruta_archivo(camara, empresa, fecha, hora)
    disponible = os.path.isfile(archivo)
    return {
        'disponible': disponible,
        'fecha': str(fecha),
        'hora': str(hora),
        'url': _resolver_url(camara, empresa, fecha, hora) if disponible else '',
        'nombre': camara.nombre,
        'ubicacion': camara.ubicacion,
    }
