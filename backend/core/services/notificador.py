"""Notificador de la fase 9: envia notificaciones via WhatsApp Business API
con canal alterno por email.

El sistema es agnostico del proveedor: si WhatsApp no esta vinculado
(`WA_VINCULADO = False`) o la API no responde, la notificacion se intenta
entregar por email (backend de consola en desarrollo/test) y se registra el
canal efectivo ('whatsapp', 'email' o 'ninguno') en la propia Notificacion.

Nunca se exponen datos sensibles: el mensaje es el texto ya construido por
`notificaciones.crear_notificacion`.
"""

import json
import logging
import urllib.request
import urllib.parse

from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppNoDisponible(Exception):
    pass


def enviar_whatsapp(numero_destino, texto):
    """Envia un mensaje por la WhatsApp Business API (meta graph).

    Devuelve la cantidad de mensajes enviados. Lanza `WhatsAppNoDisponible`
    si no hay vinculacion configurada o la API falla.
    """
    if not settings.WA_VINCULADO or not settings.WA_TOKEN:
        raise WhatsAppNoDisponible("WhatsApp no vinculado")
    if not settings.WA_NUMERO:
        raise WhatsAppNoDisponible("Remitente (WA_NUMERO) no configurado")

    payload = {
        'messaging_product': 'whatsapp',
        'from': settings.WA_NUMERO,
        'to': numero_destino,
        'type': 'text',
        'text': {'body': texto},
    }
    cuerpo = urllib.parse.urlencode(
        {'data': json.dumps(payload)}).encode()

    req = urllib.request.Request(
        settings.WA_API_URL + 'messages',
        data=cuerpo,
        headers={
            'Authorization': f'Bearer {settings.WA_TOKEN}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 300:
                raise WhatsAppNoDisponible(f"HTTP {resp.status}")
    except Exception as exc:  # noqa: BLE001
        logger.warning('WhatsApp API fallo: %s', exc)
        raise WhatsAppNoDisponible(str(exc)) from exc

    return 1


def enviar_email(numero_destino, texto):
    """Canal alterno: envia el texto por email.

    El backend se define por entorno en settings (consola en desarrollo,
    SMTP en produccion). `fail_silently` es True solo en desarrollo (DEBUG),
    para no ocultar errores reales de envio en produccion.
    """
    from django.core.mail import send_mail
    try:
        send_mail(
            subject="Notificacion InterSoft",
            message=texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[numero_destino],
            fail_silently=settings.DEBUG,
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.warning('Email fallo: %s', exc)
        return 0


def entregar(mensaje, destino_whatsapp=None, destino_email=None):
    """Entrega un texto notificando por WhatsApp y, si no es posible o no
    hay destinatario WhatsApp, por email.

    Devuelve el canal efectivo:
       'whatsapp' si se entrego por la API de WhatsApp,
       'email'    si cayo al canal alterno,
       'ninguno'  si no se pudo entregar por ningun canal.
    """
    if destino_whatsapp:
        try:
            enviar_whatsapp(destino_whatsapp, mensaje)
            return 'whatsapp'
        except WhatsAppNoDisponible:
            pass

    if destino_email:
        if enviar_email(destino_email, mensaje):
            return 'email'

    return 'ninguno'
