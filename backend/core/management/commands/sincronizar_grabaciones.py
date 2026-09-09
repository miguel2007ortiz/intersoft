"""Sincroniza la tabla `Grabacion` con los archivos .mp4 del almacenamiento.

Escanea `streams/{empresa}/{camara}/{fecha}/` bajo `MEDIA_ROOT` y hace upsert
en `core.Grabacion` (metadatos para listar y paginar en el panel de camaras).
Idempotente: agenda en cron tras la escritura de los videos por el servidor de
almacenamiento.

Uso:
    python manage.py sincronizar_grabaciones              # todas las empresas
    python manage.py sincronizar_grabaciones --empresa <uuid>
    python manage.py sincronizar_grabaciones --camara <uuid> --verbose
"""

from django.core.management.base import BaseCommand, CommandError

from core.models import Camara, Empresa
from core.services import camaras as servicio_camaras


class Command(BaseCommand):
    help = 'Hace upsert de las Grabacion con los .mp4 encontrados en disco.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa', dest='empresa',
                            help='UUID de la empresa (todas si se omite).')
        parser.add_argument('--camara', dest='camara',
                            help='UUID de la camara (todas si se omite).')
        parser.add_argument('--verbose', action='store_true',
                            help='Muestra el total de camaras revisadas.')

    def handle(self, *args, **options):
        empresa = camara = None
        if options['empresa']:
            empresa = self._obtener(Empresa, options['empresa'], 'Empresa')
        if options['camara']:
            camara = self._obtener(Camara, options['camara'], 'Camara')

        resumen = servicio_camaras.sincronizar_grabaciones(
            camara=camara, empresa=empresa)
        self.stdout.write(self.style.SUCCESS(
            f"Grabaciones sincronizadas: {resumen['creadas']} creadas, "
            f"{resumen['existentes']} existentes, "
            f"{resumen['eliminadas']} obsoletas."))
        if options['verbose']:
            self.stdout.write(f"Camaras revisadas: {resumen['camaras']}.")

    @staticmethod
    def _obtener(modelo, valor, nombre):
        try:
            return modelo.objects.get(id=valor)
        except (modelo.DoesNotExist, ValueError, TypeError):
            raise CommandError(f'{nombre} no existe: {valor}')