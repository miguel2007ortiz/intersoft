"""Recibo automatico de cada venta.

Que resuelve
------------
Hasta ahora una venta no dejaba ningun comprobante salvo que un administrador
generara a mano la factura electronica. El comprador no recibia nada y la
empresa no tenia un documento que archivar.

Recibo no es lo mismo que factura electronica
---------------------------------------------
`FacturaElectronica` es un documento fiscal: se reporta a la DIAN, lleva CUFE y
para anularla hace falta una nota credito. Por eso emitirla sigue siendo una
accion deliberada.

Un `Recibo` es solo el comprobante de la operacion. No se reporta a nadie, asi
que se puede emitir solo en cuanto la venta queda completada, sin riesgo
fiscal.

Por que una senal y no un cambio en cada vista
-----------------------------------------------
Las ventas se completan en dos sitios: el POS (`views_ventas`) y el checkout
del marketplace (`views_tienda`, cuando el pago se aprueba). Enganchar aqui
`post_save` de `Venta` cubre los dos -- y cualquiera que se anada despues --
sin tocar ninguna de esas vistas.

La senal se registra desde `CoreConfig.ready()` en un modulo propio, no dentro
de `core/signals.py`, para no cruzarse con el trabajo en curso de ese archivo.

Reglas de emision
-----------------
- Solo cuando la venta esta `completada`. Una venta `pendiente` del marketplace
  todavia no esta pagada: emitir ahi seria dar comprobante de algo sin cobrar.
- Una sola vez por venta (`OneToOne` + comprobacion previa).
- Despues del commit. Dentro de la transaccion, el recibo podria quedar escrito
  en disco y enviado por correo para una venta que despues se revierte.
- Nada de esto puede tumbar la venta: si falla la generacion o el envio, se
  registra y la venta sigue adelante.
"""

import logging

from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Recibo, Venta

logger = logging.getLogger(__name__)


def numero_de_recibo(venta) -> str:
    """`RC-` + el numero de factura interno de la venta.

    Se apoya en `numero_factura`, que ya es unico por empresa, en vez de
    llevar un contador propio: un contador nuevo se desincroniza en cuanto dos
    ventas se crean a la vez.
    """
    base = venta.numero_factura or str(venta.id)[:8].upper()
    return f"RC-{base}"


def correo_del_comprador(venta) -> str:
    """Correo al que mandar el recibo, o cadena vacia si no hay.

    Se prefiere el del `Cliente` (es el que se pide en el checkout) y se cae al
    de la cuenta si el cliente esta vinculado a un usuario del portal.
    """
    cliente = venta.cliente
    if cliente and cliente.email:
        return cliente.email
    usuario = getattr(cliente, "usuario", None)
    return usuario.email if usuario and usuario.email else ""


def construir_html(venta) -> str:
    """Comprobante en HTML con estilos de impresion (carta y ticket de 80 mm).

    Mismo criterio que los reportes: sin libreria de PDF. El navegador lo
    imprime o lo guarda como PDF, y el archivo pesa unos pocos KB.
    """
    lineas = list(venta.detalles.select_related("producto").all())
    return render_to_string("recibos/recibo.html", {
        "venta": venta,
        "empresa": venta.empresa,
        "cliente": venta.cliente,
        "lineas": lineas,
        "numero": numero_de_recibo(venta),
        "emitido": timezone.localtime(),
        "total_items": sum(linea.cantidad for linea in lineas),
    })


def enviar_por_correo(recibo, venta, html: str) -> None:
    """Manda el recibo al comprador. Un fallo se registra en el propio recibo
    y no se propaga: el comprobante ya existe y la empresa puede reenviarlo."""
    destino = correo_del_comprador(venta)
    if not destino:
        return

    texto = (
        f"Gracias por tu compra en {venta.empresa.nombre}.\n\n"
        f"Recibo: {recibo.numero}\n"
        f"Total: ${venta.total}\n\n"
        "Adjuntamos el comprobante de tu compra."
    )
    try:
        correo = EmailMultiAlternatives(
            subject=f"Recibo {recibo.numero} - {venta.empresa.nombre}",
            body=texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destino],
        )
        correo.attach_alternative(html, "text/html")
        correo.attach(f"{recibo.numero}.html", html, "text/html")
        correo.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo enviar el recibo %s a %s: %s",
                       recibo.numero, destino, exc)
        recibo.error_envio = str(exc)[:255]
        recibo.save(update_fields=["error_envio", "updated_at"])
        return

    recibo.enviado_a = destino
    recibo.enviado_en = timezone.now()
    recibo.error_envio = ""
    recibo.save(update_fields=["enviado_a", "enviado_en", "error_envio",
                               "updated_at"])


def generar_para(venta, enviar: bool = True):
    """Crea el recibo de una venta completada. Devuelve el `Recibo` o None.

    Es idempotente: si la venta ya tiene recibo se devuelve el que hay, sin
    volver a escribir el archivo ni mandar otro correo.
    """
    if venta.estado != "completada":
        return None

    recibo = Recibo.objects.filter(venta=venta).first()
    if recibo is not None:
        return recibo

    html = construir_html(venta)
    recibo = Recibo(venta=venta, numero=numero_de_recibo(venta))
    recibo.archivo.save(f"{recibo.numero}.html",
                        ContentFile(html.encode("utf-8")), save=False)
    recibo.save()

    if enviar:
        enviar_por_correo(recibo, venta, html)
    return recibo


@receiver(post_save, sender=Venta, dispatch_uid="core.recibos.emitir")
def emitir_recibo(sender, instance, **kwargs):
    """Emite el recibo cuando la venta queda completada.

    Cubre el POS y el checkout del marketplace sin tocar ninguna de las dos
    vistas. Corre `on_commit` para no generar el comprobante de una venta que
    todavia podria revertirse, y se traga cualquier error: un recibo no puede
    tumbar la venta que lo origina.
    """
    if instance.estado != "completada" or instance.deleted_at:
        return

    def emitir():
        try:
            generar_para(instance)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo al emitir el recibo de la venta %s",
                             instance.pk)

    transaction.on_commit(emitir)
