"""Comando que reintenta las notificaciones con entrega pendiente (fase 9).

Ejecuta `reintentar_entrega` para cada `Notificacion` con
`entrega_pendiente=True`, de modo que un aviso que no se pudo entregar por
WhatsApp/email se vuelva a intentar sin perderlo.
"""

from django.core.management.base import BaseCommand

from core.models import Notificacion
from core.notificaciones import reintentar_entrega


class Command(BaseCommand):
    help = ('Reintenta la entrega de las notificaciones pendientes '
            '(entrega_pendiente=True).')

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite', type=int, default=100,
            help='Maximo de notificaciones a reintentar en esta ejecucion.')

    def handle(self, *args, **options):
        pendientes = Notificacion.objects.filter(
            entrega_pendiente=True).order_by('created_at')[:options['limite']]

        reintentadas = 0
        for aviso in pendientes:
            reintentar_entrega(aviso)
            reintentadas += 1

        self.stdout.write(self.style.SUCCESS(
            f"Reintentadas {reintentadas} notificacion(es) pendientes."))
