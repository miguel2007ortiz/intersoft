import logging
from decimal import Decimal

from django.db.models import F, Subquery, Sum
from django.db.models.functions import Coalesce, Greatest
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DetalleVenta, Producto, Venta

from .analytics import invalidar_analitica

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Producto)
def alertar_stock_bajo(sender, instance, created, **kwargs):
    if instance.stock <= instance.stock_minimo and instance.activo:
        logger.warning(
            "[ALERTA STOCK] '%s' en '%s' tiene %s unidades (minimo: %s).",
            instance.nombre, instance.empresa.nombre,
            instance.stock, instance.stock_minimo,
        )


@receiver(post_save, sender=Producto)
def invalidar_cache_al_guardar_producto(sender, instance, created, **kwargs):
    invalidar_analitica()


@receiver([post_save, post_delete], sender=Venta)
def invalidar_cache_al_guardar_venta(sender, instance, **kwargs):
    invalidar_analitica()


def recalcular_totales_venta(venta: Venta) -> None:
    """Mantiene la integridad financiera de una venta a partir de sus lineas.

    Recalcula ``subtotal`` como la suma de ``cantidad * precio_unitario`` de sus
    detalles y persiste ``total = subtotal - descuento`` (nunca negativo),
    conservando el ``descuento`` ya aplicado (cupon o POS). Si la venta carece
    de lineas, se pone subtotal/total en 0.

    El calculo y la escritura se hacen en UN SOLO ``UPDATE`` via ``Subquery``,
    de modo que la BD lee los detalles con un current read: evita ver un
    snapshot inconsistente de MySQL REPEATABLE READ cuando la senal corre en
    la misma transaccion que crea/borra la linea (post_save / post_delete).
    """
    subtotal_subquery = (
        DetalleVenta.objects.filter(venta=venta.pk)
        .annotate(linea_total=F('cantidad') * F('precio_unitario'))
        .values('venta_id')
        .annotate(suma=Sum('linea_total'))
        .values('suma')
    )
    descuento = venta.descuento if venta.descuento is not None else Decimal('0')
    Venta.objects.filter(pk=venta.pk).update(
        subtotal=Coalesce(Subquery(subtotal_subquery), Decimal('0')),
        total=Greatest(
            Coalesce(Subquery(subtotal_subquery), Decimal('0')) - descuento,
            Decimal('0'),
        ),
    )


@receiver([post_save, post_delete], sender=DetalleVenta)
def mantener_totales_venta(sender, instance, **kwargs):
    """Reconstruye los totales de la venta tras crear/editar/quitar una linea."""
    try:
        recalcular_totales_venta(instance.venta)
    except Venta.DoesNotExist:
        # La venta padre pudo eliminarse en cascada junto con sus detalles.
        return
