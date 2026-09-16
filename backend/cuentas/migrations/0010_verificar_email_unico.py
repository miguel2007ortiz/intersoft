"""Verificacion previa a la unicidad de `auth_user.email`.

La migracion 0005 anade el indice UNIQUE con SQL directo. Sobre una base que
ya tenga correos repetidos, MySQL aborta con un `Duplicate entry '...' for key
'uniq_auth_user_email'` que no dice cuantas cuentas hay que arreglar ni
cuales. Esta migracion corre ANTES de asegurar el indice y aborta con la lista
concreta de correos duplicados y de los ids implicados.

Tambien crea el indice si falta (bases anteriores a 0005, o entornos donde se
elimino a mano), de forma idempotente: asi la garantia de "un correo = una
cuenta" en la que se apoya la resolucion de identidad del login no depende de
que 0005 se haya aplicado.
"""

from django.db import migrations

NOMBRE_INDICE = "uniq_auth_user_email"


def _indice_existe(cursor) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() AND table_name = 'auth_user' "
        "AND index_name = %s",
        [NOMBRE_INDICE],
    )
    return cursor.fetchone()[0] > 0


def verificar_y_asegurar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        # La comparacion usa LOWER() porque el login resuelve el correo con
        # `iexact`: dos filas que solo difieran en mayusculas tambien son un
        # duplicado desde el punto de vista de la identidad.
        cursor.execute(
            "SELECT LOWER(email) AS correo, COUNT(*) AS cuantos, "
            "       GROUP_CONCAT(id ORDER BY id) AS ids "
            "FROM auth_user WHERE email <> '' "
            "GROUP BY LOWER(email) HAVING COUNT(*) > 1 ORDER BY cuantos DESC"
        )
        duplicados = cursor.fetchall()

        if duplicados:
            detalle = "\n".join(
                f"  - {correo}: {cuantos} cuentas (auth_user.id = {ids})"
                for correo, cuantos, ids in duplicados
            )
            raise RuntimeError(
                "No se puede aplicar la unicidad de correo: hay "
                f"{len(duplicados)} correo(s) repetido(s) en auth_user.\n"
                f"{detalle}\n\n"
                "Con correos repetidos el login no puede resolver la identidad "
                "de forma deterministica (elegia un perfil arbitrario). "
                "Resuelvelos antes de migrar: deja una sola cuenta por correo "
                "y cambia o vacia el correo de las demas. Para revisarlos sin "
                "migrar: python manage.py verificar_emails_duplicados"
            )

        if not _indice_existe(cursor):
            cursor.execute(
                f"ALTER TABLE `auth_user` ADD UNIQUE KEY `{NOMBRE_INDICE}` (`email`);"
            )


def revertir(apps, schema_editor):
    """No se elimina el indice: 0005 es la duena de su creacion y quien debe
    revertirlo. Esta migracion solo verifica y repara."""


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0009_perfil_datos_laborales"),
    ]

    operations = [
        migrations.RunPython(verificar_y_asegurar, revertir),
    ]
