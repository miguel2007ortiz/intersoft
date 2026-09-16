"""Genera las alertas de stock bajo pendientes (backfill).

El signal de `Producto` mantiene la alerta global por producto a partir de
ahora, pero los productos que ya estaban en stock bajo antes de esta
funcionalidad no tienen su `Notificacion`. Este comando recorre los productos
activos y crea/actualiza la alerta de cada uno que este en stock bajo
(idempotente: no duplica, usa `sincronizar_alerta_stock`).

Uso:
    python manage.py generar_alertas_stock                # todas las empresas
    python manage.py generar_alertas_stock --empresa <uuid>
"""

from django.core.management.base import BaseCommand

from core.models import Producto
from core.notificaciones import sincronizar_alerta_stock


class Command(BaseCommand):
    help = 'Reconstruye las alertas de stock bajo para los productos agotados.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa', dest='empresa',
                            help='UUID de la empresa (todas si se omite).')

    def handle(self, *args, **options):
        productos = (Producto.objects.filter(deleted_at__isnull=True, activo=True)
                     .select_related('empresa'))
        if options['empresa']:
            productos = productos.filter(empresa_id=options['empresa'])

        creadas = pendientes = 0
        for producto in productos.iterator(chunk_size=500):
            alerta = sincronizar_alerta_stock(producto)
            if alerta is not None:
                creadas += 1
            if producto.stock <= producto.stock_minimo:
                pendientes += 1

        self.stdout.write(self.style.SUCCESS(
            f'{creadas} alertas creadas o actualizadas '
            f'({pendientes} productos en stock bajo).'))