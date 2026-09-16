"""Detecta identidades ambiguas en `auth_user` antes de migrar.

El login resuelve la identidad por correo y `authenticate()` por `username`,
asi que un valor repetido -- ignorando mayusculas -- hace que el contexto
(empresa, rol, permisos) y el conteo de intentos fallidos puedan caer en una
cuenta distinta de la que se esta abriendo (BUG-09).

La migracion `cuentas.0012_email_unico_sin_mayusculas` aborta si encuentra
duplicados; este comando permite revisarlos sin lanzar la migracion.

Uso:
    python manage.py verificar_emails_duplicados

Salida: 0 si no hay duplicados, 1 si los hay.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from cuentas.identidad import buscar, describir


class Command(BaseCommand):
    help = ("Lista los correos y usuarios repetidos en auth_user ignorando "
            "mayusculas (bloquean la unicidad de identidad).")

    def handle(self, *args, **opciones):
        with connection.cursor() as cursor:
            hallazgos = buscar(cursor)

        if not hallazgos:
            self.stdout.write(self.style.SUCCESS(
                "Sin identidades duplicadas: un correo = un usuario = una cuenta."))
            return

        self.stdout.write(self.style.ERROR(describir(hallazgos)))
        cuantas = sum(len(filas) for filas in hallazgos.values())
        raise CommandError(
            f"{cuantas} identidad(es) duplicada(s) ignorando mayusculas. Deja "
            "una sola cuenta por correo y por usuario antes de aplicar la "
            "unicidad."
        )
