"""Servicio de camaras (fase 9): resolucion y catalogo de grabaciones.

Las grabaciones historicas viven en disco bajo
`{MEDIA_URL}streams/{empresa_id.hex}/{camara_id.hex}/{fecha}/{hora}.mp4`.
Por si solas se buscan por fecha/hora (`resolver_grabacion`); `Grabacion`
mantiene en BD el catalogo por camara (metadatos para listar y paginar) que
`sincronizar_grabaciones` reconstruye escaneando ese mismo directorio.

Si el archivo no existe (o no hay servidor de almacenamiento real) se
devuelve `disponible=False` y el panel mostrara un aviso en lugar de un
reproductor roto.
"""

import os
from datetime import datetime

from django.conf import settings
from django.db.models import Q

from ..models import Camara, Grabacion


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


def disponible_y_url(grabacion):
    """True + URL si el archivo de la grabacion sigue existiendo en disco."""
    archivo = _ruta_archivo(
        grabacion.camara, grabacion.camara.empresa,
        grabacion.fecha, grabacion.hora)
    if os.path.isfile(archivo):
        return True, _resolver_url(
            grabacion.camara, grabacion.camara.empresa,
            grabacion.fecha, grabacion.hora)
    return False, ''


def sincronizar_grabaciones(camara=None, empresa=None):
    """Escanea `streams/` y hace upsert de los metadatos en `Grabacion`.

    Por cada archivo `{fecha}/{HH_MM}.mp4` se crea la fila (camara, fecha,
    hora) con su tamano; las filas cuyo archivo ya no existe se eliminan
    (video movido o purgado). Idempotente. Filtrable por empresa y/o camara
    para sincronizaciones parciales (command `sincronizar_grabaciones`).

    Devuelve {'creadas': n, 'existentes': n, 'eliminadas': n, 'camaras': n}.
    """
    qs = Camara.objects.filter(deleted_at__isnull=True).order_by('id')
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    if camara is not None:
        qs = qs.filter(id=camara.id)

    creadas = existentes = eliminadas = camaras = 0
    for cam in qs:
        camaras += 1
        base = os.path.join(
            str(settings.MEDIA_ROOT), 'streams',
            cam.empresa_id.hex, cam.id.hex)
        if not os.path.isdir(base):
            continue

        vistos = []
        for nombre_fecha in os.listdir(base):
            dir_fecha = os.path.join(base, nombre_fecha)
            if not os.path.isdir(dir_fecha):
                continue
            try:
                fecha = datetime.strptime(nombre_fecha, '%Y-%m-%d').date()
            except ValueError:
                continue
            for nombre_hora in sorted(os.listdir(dir_fecha)):
                if not nombre_hora.endswith('.mp4'):
                    continue
                try:
                    hora = datetime.strptime(nombre_hora, '%H_%M.mp4').time()
                except ValueError:
                    continue
                vistos.append((fecha, hora))
                tamano = os.path.getsize(os.path.join(dir_fecha, nombre_hora))
                _, creado = Grabacion.objects.get_or_create(
                    camara=cam, fecha=fecha, hora=hora,
                    defaults={'archivo': _ruta_archivo(cam, cam.empresa, fecha, hora),
                              'tamano_bytes': tamano})
                if creado:
                    creadas += 1
                else:
                    Grabacion.objects.filter(camara=cam, fecha=fecha, hora=hora)\
                        .update(tamano_bytes=tamano)
                    existentes += 1

        obsoletas = Grabacion.objects.filter(camara=cam)
        if vistos:
            condicion = Q(fecha=vistos[0][0], hora=vistos[0][1])
            for fecha, hora in vistos[1:]:
                condicion = condicion | Q(fecha=fecha, hora=hora)
            obsoletas = obsoletas.exclude(condicion)
        eliminadas += obsoletas.count()
        obsoletas.delete()

    return {'creadas': creadas, 'existentes': existentes,
            'eliminadas': eliminadas, 'camaras': camaras}
