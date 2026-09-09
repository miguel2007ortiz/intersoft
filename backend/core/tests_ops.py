"""Backups y monitoreo (RIESGOS #6): comandos `backup_db` y `monitor`.

Cubren sin tocar MySQL real:
- backup_db: genera el dump con mysqldump, pasa la password por MYSQL_PWD
  (nunca en argv), rota respaldos viejos, y con --verify restaura en una
  BD temporal y la elimina al final.
- monitor: exit 0 cuando todo esta en orden y exit 1 cuando un chequeo
  falla (BD caida, migraciones pendientes, cache roto, disco al minimo o
  respaldo vencido).
"""

import os
import subprocess  # nosec B404
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.db import OperationalError
from django.test import TestCase, override_settings

patch_targets = {
    "backup": "core.management.commands.backup_db",
    "monitor": "core.management.commands.monitor",
}


class BackupDbTest(TestCase):
    """Usa un directorio temporal; mysqldump/mysql van mockeados."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="intersoft_backup_test_"))
        self.override = override_settings(
            BACKUP_DIR=str(self.tmp), BACKUP_RETENER_DIAS=7
        )
        self.override.enable()

    def tearDown(self):
        self.override.disable()

    def test_genera_dump_con_password_por_env_y_rota_antiguos(self):
        viejo = self.tmp / "backup_test_intersoft1_db_20200101-000000.sql"
        viejo.touch()
        momento_viejo = datetime.now().timestamp() - 10 * 86400
        os.utime(viejo, (momento_viejo, momento_viejo))
        reciente = self.tmp / "backup_test_intersoft1_db_20260101-000000.sql"
        reciente.touch()

        with (
            patch.object(settings, "MYSQLDUMP_BIN", "C:/fake/mysqldump.exe"),
            patch(
                f'{patch_targets["backup"]}.subprocess.run',
                return_value=subprocess.CompletedProcess([], 0),
            ) as ejecutar,
        ):
            call_command("backup_db")

        self.assertFalse(viejo.exists(), "el respaldo de hace 10 dias se borra")
        self.assertTrue(reciente.exists())
        nuevos = list(self.tmp.glob("backup_test_intersoft1_db_*.sql"))
        self.assertEqual(len(nuevos), 2)  # el reciente de prueba + el nuevo

        llamada = ejecutar.call_args
        self.assertIn("env", llamada.kwargs)
        self.assertIn("MYSQL_PWD", llamada.kwargs["env"])
        self.assertNotIn("password", " ".join(llamada.args[0]).lower())

    def test_verify_restaura_y_elimina_la_base_temporal(self):
        def falsa_proceso(*args, **kwargs):
            salida = ("12" if "-N" in args[0] else "") if kwargs.get("text") else b""
            return subprocess.CompletedProcess(args[0], 0, stdout=salida)

        with (
            patch.object(settings, "MYSQLDUMP_BIN", "C:/fake/mysqldump.exe"),
            patch.object(settings, "MYSQL_BIN", "C:/fake/mysql.exe"),
            patch(
                f'{patch_targets["backup"]}.subprocess.run',
                side_effect=falsa_proceso,
            ) as ejecutar,
        ):
            call_command("backup_db", "--verify")

        llamadas = [c.args[0] for c in ejecutar.call_args_list]
        # mysqldump (dump) + mysql -e (crear) + mysql temporal (restore)
        # + mysql -e (contar) + mysql -e (drop): minimo 4 procesos mysql.
        self.assertGreaterEqual(len(llamadas), 5)
        create = llamadas[1]
        self.assertIn("-e", create)
        texto = " ".join(create)
        self.assertIn("CREATE DATABASE intersoft_backup_verificacion_", texto)
        drop = llamadas[-1]
        self.assertIn(
            "DROP DATABASE IF EXISTS intersoft_backup_verificacion_", " ".join(drop)
        )
        # el restore abre el dump como stdin (sin pasarlo por argv/shell).
        restore = llamadas[2]
        self.assertEqual(restore[-1].startswith("intersoft_backup_verificacion_"), True)

    def test_falla_con_mensaje_claro_si_mysqldump_no_existe(self):
        with (
            patch(f'{patch_targets["backup"]}.shutil.which', return_value=None),
            patch.object(settings, "MYSQLDUMP_BIN", ""),
        ):
            from django.core.management.base import CommandError

            with self.assertRaises(CommandError) as ctx:
                call_command("backup_db")
            self.assertIn("MYSQLDUMP_BIN", str(ctx.exception))

    def test_mysqldump_roto_propaga_commanderror(self):
        with (
            patch.object(settings, "MYSQLDUMP_BIN", "C:/fake/mysqldump.exe"),
            patch(
                f'{patch_targets["backup"]}.subprocess.run',
                side_effect=subprocess.CalledProcessError(1, "mysqldump"),
            ),
        ):
            from django.core.management.base import CommandError

            with self.assertRaises(CommandError):
                call_command("backup_db")


@override_settings(MONITOR_ALERTA_BACKUP_HORAS=24)
class MonitorTest(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="intersoft_monitor_test_"))
        self.override = override_settings(BACKUP_DIR=str(self.tmp))
        self.override.enable()
        self._nuevo()  # respaldo fresco para que el chequeo pase

    def tearDown(self):
        self.override.disable()

    def _nuevo(self, nombre="backup_test_intersoft1_db_20260101-000000.sql"):
        archivo = self.tmp / nombre
        archivo.touch()
        os.utime(archivo, (datetime.now().timestamp(), datetime.now().timestamp()))
        return archivo

    def test_todo_ok_no_lanza(self):
        with (
            patch.object(settings, "MONITOR_ALERTA_BACKUP_HORAS", 24),
            patch(f'{patch_targets["monitor"]}.connection') as conexion,
            patch(f'{patch_targets["monitor"]}.MigrationExecutor') as ejec,
            patch(f'{patch_targets["monitor"]}.cache') as cache,
        ):
            conexion.cursor.return_value.__enter__.return_value = mock.MagicMock()
            ejec.return_value.migration_plan.return_value = []
            cache.set.return_value = None
            cache.get.return_value = 1
            call_command("monitor")  # no debe lanzar SystemExit

    def test_bd_caida_sale_con_codigo_1(self):
        with patch(f'{patch_targets["monitor"]}.connection') as conexion:
            conexion.cursor.side_effect = OperationalError("server closed")
            with self.assertRaises(SystemExit) as ctx:
                call_command("monitor")
            self.assertEqual(ctx.exception.code, 1)

    def test_respaldo_viejo_sale_con_codigo_1(self):
        for nombre in os.listdir(self.tmp):
            (self.tmp / nombre).unlink()
        self._nuevo("backup_test_intersoft1_db_20200101-000000.sql")
        momento_viejo = datetime.now().timestamp() - 48 * 3600
        for nombre in os.listdir(self.tmp):
            os.utime(self.tmp / nombre, (momento_viejo, momento_viejo))
        with self.assertRaises(SystemExit) as ctx:
            call_command("monitor", **{"backup_dir": str(self.tmp)})
        self.assertEqual(ctx.exception.code, 1)

    def test_sin_respaldos_sale_con_codigo_1(self):
        for nombre in os.listdir(self.tmp):
            (self.tmp / nombre).unlink()
        with self.assertRaises(SystemExit) as ctx:
            call_command("monitor", **{"backup_dir": str(self.tmp)})
        self.assertEqual(ctx.exception.code, 1)

    def test_media_inexistente_sale_con_codigo_1(self):
        inexistente = self.tmp / "media_no_existe"
        with patch.object(settings, "MEDIA_ROOT", str(inexistente)):
            with self.assertRaises(SystemExit) as ctx:
                call_command("monitor")
        self.assertEqual(ctx.exception.code, 1)
