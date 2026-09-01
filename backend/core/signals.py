import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Producto

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Producto)
def alertar_stock_bajo(sender, instance, created, **kwargs):
    if instance.stock <= instance.stock_minimo and instance.activo:
        logger.warning(
            "[ALERTA STOCK] '%s' en '%s' tiene %s unidades (minimo: %s).",
            instance.nombre, instance.empresa.nombre,
            instance.stock, instance.stock_minimo,
        )
