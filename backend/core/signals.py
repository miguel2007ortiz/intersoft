from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Producto


@receiver(post_save, sender=Producto)
def alertar_stock_bajo(sender, instance, created, **kwargs):
    if instance.stock <= instance.stock_minimo and instance.activo:
        print(
            f"[ALERTA STOCK] '{instance.nombre}' en "
            f"'{instance.empresa.nombre}' tiene {instance.stock} "
            f"unidades (minimo: {instance.stock_minimo})."
        )
