"""Chequeo de salud del sistema (RIESGOS #6 - backups y monitoreo).

`python manage.py monitor` verifica: conexion a la BD, migraciones al dia,
cache funcional, espacio libre en disco y antiguedad del ultimo respaldo
generado por `backup_db`. Sale con codigo 1 si algo falla (para cron/CI)
y 0 en caso contrario. Nunca imprime secretos ni credenciales.
"""

import os
import shutil
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

DISCOS_MINIMO_LIBRE = 1024**3  # 1 GiB de margen sobre el backup_dir


class Command(BaseCommand):
    help = (
        "Verifica la salud del sistema (BD, migraciones, cache, disco, "
        "antiguedad del ultimo respaldo) y sale con codigo 1 si algo "
        "falla."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--backup-dir",
            default=None,
            help="Directorio de respaldos a inspeccionar " "(default: BACKUP_DIR).",
        )

    def handle(self, *args, **options):
        fallos = 0

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            self._ok("Base de datos: conexion OK")
        except Exception as exc:
            fallos += 1
            self._fallo("Base de datos", exc)

        try:
            executor = MigrationExecutor(connection)
            pendientes = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if pendientes:
                fallos += 1
                self._fallo(
                    "Migraciones",
                    f"{len(pendientes)} pendiente(s) " "por aplicar (migrate).",
                )
            else:
                self._ok("Migraciones: al dia")
        except Exception as exc:
            fallos += 1
            self._fallo("Migraciones", exc)

        try:
            clave = "monitor:ping"
            cache.set(clave, 1, 5)
            if cache.get(clave) == 1:
                self._ok("Cache: lectura/escritura OK")
            else:
                fallos += 1
                self._fallo("Cache", "no devolvio el valor de prueba.")
        except Exception as exc:
            fallos += 1
            self._fallo("Cache", exc)

        backup_dir = settings.BACKUP_DIR
        if options["backup_dir"]:
            backup_dir = options["backup_dir"]
        try:
            disco = shutil.disk_usage(backup_dir)
            libre_gib = disco.free / (1024**3)
            if disco.free < DISCOS_MINIMO_LIBRE:
                fallos += 1
                self._fallo(
                    "Disco",
                    f"solo {libre_gib:.1f} GiB libres en "
                    f"{backup_dir} (minimo 1 GiB).",
                )
            else:
                self._ok(f"Disco: {libre_gib:.1f} GiB libres")
        except OSError as exc:
            fallos += 1
            self._fallo("Disco", f"{backup_dir}: {exc}")

        try:
            media_dir = settings.MEDIA_ROOT
            if not os.path.isdir(media_dir):
                fallos += 1
                self._fallo("Media", f"{media_dir} no existe (MEDIA_ROOT).")
            elif not os.access(media_dir, os.W_OK):
                fallos += 1
                self._fallo("Media", f"{media_dir} no es escribible.")
            else:
                self._ok(f"Media: {media_dir} existe y es escribible")
        except OSError as exc:
            fallos += 1
            self._fallo("Media", exc)

        nombre_db = settings.DATABASES["default"]["NAME"]
        fallos += self._revisar_respaldo(backup_dir, nombre_db)

        if fallos:
            self.stderr.write(
                self.style.ERROR(f"Monitor: {fallos} problema(s) detectado(s).")
            )
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Monitor: todo en orden."))

    def _revisar_respaldo(self, backup_dir, nombre_db):
        respaldos = (
            sorted(
                os.path.join(backup_dir, nombre)
                for nombre in os.listdir(backup_dir)
                if nombre.startswith(f"backup_{nombre_db}_") and nombre.endswith(".sql")
            )
            if os.path.isdir(backup_dir)
            else []
        )
        if not respaldos:
            self._fallo(
                "Respaldo",
                f"no hay respaldos `backup_{nombre_db}_*.sql` " f"en {backup_dir}.",
            )
            return 1
        ultimo = respaldos[-1]
        edad_horas = (datetime.now().timestamp() - os.path.getmtime(ultimo)) / 3600
        if edad_horas > settings.MONITOR_ALERTA_BACKUP_HORAS:
            self._fallo(
                "Respaldo", f"el mas reciente ({ultimo}) tiene " f"{edad_horas:.1f} h."
            )
            return 1
        self._ok(f"Respaldo reciente ({edad_horas:.1f} h): {ultimo}")
        return 0

    def _ok(self, mensaje):
        self.stdout.write(self.style.SUCCESS(f"  ok  {mensaje}"))

    def _fallo(self, componente, detalle):
        self.stderr.write(self.style.ERROR(f"  FALLO  {componente}: {detalle}"))
