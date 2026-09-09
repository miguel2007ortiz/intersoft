"""Respaldo MySQL del proyecto (RIESGOS #6 - backups y monitoreo).

`python manage.py backup_db` genera un dump .sql con mysqldump en
BACKUP_DIR, con rotacion por antiguedad (BACKUP_RETENER_DIAS). Con
`--verify` restaura el dump en una base temporal, comprueba que carga y la
elimina al terminar (verificacion real de que el respaldo sirve).

La password de MySQL se pasa por la variable de entorno MYSQL_PWD del
proceso hijo (nunca en la linea de comandos, donde quedaria visible).
"""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _comando(nombre, setting_env, sugerencia):
    """Devuelve la ruta al binario o CommandError con la pista para configurarlo."""
    ruta = getattr(settings, setting_env, "") or shutil.which(nombre)
    if not ruta:
        raise CommandError(f"No se encontro '{nombre}' en el PATH. {sugerencia}")
    return ruta


class Command(BaseCommand):
    help = (
        "Genera un respaldo .sql de la base de datos en BACKUP_DIR "
        "con rotacion por antiguedad y verificacion opcional de restore."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino", default=None, help="Directorio destino (default: BACKUP_DIR)."
        )
        parser.add_argument(
            "--retener",
            type=int,
            default=None,
            help="Dias de respaldos a conservar " "(default: BACKUP_RETENER_DIAS).",
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Restaura el dump en una base temporal, "
            "comprueba las tablas y la elimina.",
        )
        parser.add_argument(
            "--no-rotacion", action="store_true", help="No borra respaldos antiguos."
        )

    def handle(self, *args, **options):
        destino = Path(options["destino"] or settings.BACKUP_DIR)
        retener = options["retener"] or settings.BACKUP_RETENER_DIAS
        db = settings.DATABASES["default"]

        destino.mkdir(parents=True, exist_ok=True)
        if not os.access(destino, os.W_OK):
            raise CommandError(
                f"El directorio de respaldo no es escribible: " f"{destino}"
            )

        nombre = f"backup_{db['NAME']}_{datetime.now():%Y%m%d-%H%M%S}.sql"
        ruta = destino / nombre
        entorno = dict(os.environ)
        entorno["MYSQL_PWD"] = db.get("PASSWORD", "")
        mysqldump = _comando(
            "mysqldump",
            "MYSQLDUMP_BIN",
            "Indica la ruta con la variable de entorno MYSQLDUMP_BIN.",
        )

        comando = [
            mysqldump,
            "--single-transaction",
            "--routines",
            "--triggers",
            "--no-tablespaces",
            "--default-character-set=utf8mb4",
            "--host",
            str(db.get("HOST", "127.0.0.1")),
            "--port",
            str(db.get("PORT", "3306")),
            "--user",
            str(db.get("USER", "root")),
            str(db["NAME"]),
        ]
        try:
            with open(ruta, "wb") as salida:
                subprocess.run(comando, env=entorno, check=True, stdout=salida)
        except FileNotFoundError as exc:
            raise CommandError(f"No se pudo ejecutar '{mysqldump}': {exc}") from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"mysqldump fallo con codigo {exc.returncode}") from exc

        self.stdout.write(self.style.SUCCESS(f"Respaldo creado: {ruta}"))

        if options["verify"]:
            self._verificar_restore(ruta, db, entorno)

        if not options["no_rotacion"]:
            self._rotar(destino, db["NAME"], retener)

    def _verificar_restore(self, ruta, db, entorno):
        temporal = f"intersoft_backup_verificacion_{datetime.now():%H%M%S}"
        mysql = _comando(
            "mysql", "MYSQL_BIN", "Indica la ruta con la variable de entorno MYSQL_BIN."
        )
        host = str(db.get("HOST", "127.0.0.1"))
        puerto = str(db.get("PORT", "3306"))
        usuario = str(db.get("USER", "root"))
        base = [mysql, "--host", host, "--port", puerto, "--user", usuario]
        try:
            subprocess.run(
                base
                + [
                    "-e",
                    f"DROP DATABASE IF EXISTS {temporal}; "
                    f"CREATE DATABASE {temporal} "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci;",
                ],
                env=entorno,
                check=True,
                capture_output=True,
            )
            with open(ruta, "rb") as dump:
                subprocess.run(
                    base + [temporal],
                    env=entorno,
                    check=True,
                    stdin=dump,
                    capture_output=True,
                )
            conteo = subprocess.run(
                base
                + [
                    "-N",
                    "-e",
                    f"SELECT COUNT(*) FROM information_schema.tables "
                    f"WHERE table_schema = '{temporal}';",
                ],
                env=entorno,
                check=True,
                capture_output=True,
                text=True,
            )
            tablas = int(conteo.stdout.strip() or 0)
            if tablas == 0:
                raise CommandError(
                    "La restauracion no encontro tablas (0). El respaldo "
                    "esta vacio o corrupto."
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Restore verificado en '{temporal}' " f"({tablas} tablas)."
                )
            )
        finally:
            subprocess.run(
                base + ["-e", f"DROP DATABASE IF EXISTS {temporal};"],
                env=entorno,
                capture_output=True,
            )

    def _rotar(self, destino, nombre_db, retener):
        limite = datetime.now() - timedelta(days=retener)
        borrados = 0
        for archivo in destino.glob(f"backup_{nombre_db}_*.sql"):
            if datetime.fromtimestamp(archivo.stat().st_mtime) < limite:
                archivo.unlink(missing_ok=True)
                borrados += 1
        if borrados:
            self.stdout.write(
                self.style.WARNING(
                    f"Rotacion: se borraron {borrados} respaldo(s) "
                    f"con mas de {retener} dia(s)."
                )
            )
