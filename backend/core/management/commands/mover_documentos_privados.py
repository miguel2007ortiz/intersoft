"""Mueve los comprobantes ya generados de `MEDIA_ROOT` a `DOCUMENTOS_ROOT`.

Complemento de la migracion `0024_documentos_privados`, que cambia el `storage`
de los campos pero no toca el disco. Los archivos escritos antes de ese cambio
siguen bajo `MEDIA_ROOT`, donde el nuevo storage no los busca: sin este paso la
descarga responde 410 (`COMPROBANTE_NO_DISPONIBLE`) aunque la fila exista.

La ruta guardada en la base de datos no cambia -- es relativa
(`facturas/2026/09/pdf/FE-FT-00002.pdf`) y vale igual en las dos carpetas --, asi
que el comando no escribe en la base de datos: solo mueve ficheros.

Idempotente: si el destino ya existe, no hace nada. Se puede correr dos veces, o
retomar una corrida interrumpida a mitad.

Uso:
    python manage.py mover_documentos_privados --dry-run   # solo informa
    python manage.py mover_documentos_privados
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import FacturaElectronica, NotaCredito, Recibo

# (modelo, campos). Los mismos que la migracion 0024 pasa a DOCUMENTOS_ROOT.
CAMPOS = [
    (FacturaElectronica, ('pdf', 'xml')),
    (NotaCredito, ('pdf', 'xml')),
    (Recibo, ('archivo',)),
]


class Command(BaseCommand):
    help = ('Mueve facturas, notas credito y recibos de MEDIA_ROOT a '
            'DOCUMENTOS_ROOT (no toca la base de datos).')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', dest='dry_run',
                            help='Informa que se moveria, sin tocar el disco.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        origen_base = Path(settings.MEDIA_ROOT)
        destino_base = Path(settings.DOCUMENTOS_ROOT)

        if origen_base == destino_base:
            self.stdout.write(self.style.WARNING(
                'MEDIA_ROOT y DOCUMENTOS_ROOT son la misma carpeta; no hay '
                'nada que mover. Revisa la configuracion: los comprobantes '
                'deben quedar fuera de MEDIA_ROOT.'))
            return

        movidos = ya_estaban = perdidos = 0

        for modelo, nombres in CAMPOS:
            # `all_objects` no existe en estos modelos; el borrado logico no
            # borra el archivo, asi que las filas inactivas tambien se mueven.
            for fila in modelo.objects.all():
                for nombre_campo in nombres:
                    archivo = getattr(fila, nombre_campo)
                    if not archivo:
                        continue

                    ruta = archivo.name
                    origen = origen_base / ruta
                    destino = destino_base / ruta

                    if destino.exists():
                        ya_estaban += 1
                        continue

                    if not origen.exists():
                        perdidos += 1
                        self.stdout.write(self.style.WARNING(
                            f'  falta en disco: {ruta} '
                            f'({modelo.__name__} {fila.pk})'))
                        continue

                    if dry_run:
                        self.stdout.write(f'  moveria: {ruta}')
                    else:
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(origen), str(destino))
                    movidos += 1

        verbo = 'se moverian' if dry_run else 'movidos'
        self.stdout.write(self.style.SUCCESS(
            f'{verbo}: {movidos} | ya en destino: {ya_estaban} | '
            f'sin archivo en disco: {perdidos}'))
        if perdidos and not dry_run:
            self.stdout.write(
                'Las filas sin archivo en disco quedan igual que antes: la '
                'descarga responde 410 y el comprobante se puede regenerar.')
