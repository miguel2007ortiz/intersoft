import logging

from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def manejador_excepciones(exc, context):
    """Envuelve el manejador de DRF: los errores no controlados (p. ej. una
    caida de la base de datos) se registran en el log del servidor y al
    cliente solo se le devuelve un mensaje generico, sin trazas ni datos
    de conexion.

    El 429 por throttling se normaliza al mismo contrato de errores de la
    API ({codigo, detalle, errores}) para que el frontend no dependa de la
    forma por defecto de DRF ({"detail": ...}).
    """
    if isinstance(exc, Throttled):
        return Response(
            {"codigo": "THROTTLED",
             "detalle": "Demasiadas peticiones desde esta IP. Intenta de nuevo en unos minutos.",
             "errores": None},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.exception('Error no controlado en %s', context.get('view'))
    return Response(
        {'detail': 'Ocurrio un error inesperado. Intenta de nuevo en unos minutos.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
