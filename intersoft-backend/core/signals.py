"""
Señales de InterSoft.

Replican en Python parte de la lógica que en PostgreSQL vivía en triggers.
Aquí: detectar stock bajo tras guardar un producto.

En una arquitectura real esto dispararía una notificación (email, push,
WhatsApp). Por ahora deja constancia en consola.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Producto


@receiver(post_save, sender=Producto)
def alertar_stock_bajo(sender, instance, created, **kwargs):
    """
    Tras guardar un Producto, verifica si su stock cayó al mínimo.
    Equivalente al trigger 'tr_alerta_stock' del modelo SQL.
    """
    if instance.stock <= instance.stock_minimo and instance.activo:
        print(
            f"[ALERTA STOCK] '{instance.nombre}' en "
            f"'{instance.empresa.nombre}' tiene {instance.stock} "
            f"unidades (mínimo: {instance.stock_minimo})."
        )
        # TODO: integrar con un sistema de notificaciones real.
