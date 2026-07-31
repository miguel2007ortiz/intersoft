#!/usr/bin/env python
"""Utilidad de linea de comandos de Django para tareas administrativas."""
import os
import sys

# ════════════════════════════════════════════════════════════
# VERIFICACION DE VERSION DE PYTHON
# Este proyecto se desarrollo para Python 3.14.
# Django 5.2 LTS requiere Python 3.10 o superior.
# Fallar aqui con un mensaje claro es mejor que un error confuso
# a mitad del arranque.
# ════════════════════════════════════════════════════════════
VERSION_MINIMA = (3, 10)
VERSION_OBJETIVO = (3, 14)

if sys.version_info < VERSION_MINIMA:
    sys.exit(
        f"\nERROR: InterSoft necesita Python {VERSION_MINIMA[0]}.{VERSION_MINIMA[1]} o superior.\n"
        f"       Tu version actual es {sys.version_info.major}.{sys.version_info.minor}.\n"
        f"       Version recomendada para este proyecto: 3.14.6\n"
    )

if sys.version_info[:2] != VERSION_OBJETIVO:
    print(
        f"AVISO: este proyecto se desarrollo para Python "
        f"{VERSION_OBJETIVO[0]}.{VERSION_OBJETIVO[1]}. "
        f"Estas usando {sys.version_info.major}.{sys.version_info.minor}. "
        f"Deberia funcionar, pero puede haber diferencias.",
        file=sys.stderr,
    )


def main():
    """Ejecuta tareas administrativas."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intersoft.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Esta instalado y disponible en tu "
            "PYTHONPATH? Olvidaste activar el entorno virtual?\n"
            "Recuerda: Django 5.2+ es obligatorio para Python 3.14."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
