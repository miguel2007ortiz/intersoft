from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Crea la tabla del cache por base de datos si no existe (B1).'

    def handle(self, *args, **options):
        try:
            call_command('createcachetable', verbosity=0)
            self.stdout.write('Tabla del cache listo (creada o ya existia).')
        except CommandError as exc:
            if 'already exist' in str(exc).lower():
                self.stdout.write(self.style.WARNING(
                    'La tabla del cache ya existia; no se creo nada.'))
            else:
                raise