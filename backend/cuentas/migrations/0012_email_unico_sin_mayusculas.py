"""Unicidad de identidad que NO depende de la collation de la base.

`0005` creo un UNIQUE normal sobre `auth_user.email`. Ese indice solo ignora
mayusculas porque la collation por defecto de MySQL (`utf8mb4_0900_ai_ci`) lo
hace: en una base creada con `utf8mb4_bin` -- o al cambiar de motor --
`Ana@elprogreso.co` y `ana@elprogreso.co` volverian a convivir y con ellas el
BUG-09 (el login resolviendo una identidad ambigua).

Esta migracion:
  1. Aborta si ya hay identidades repetidas ignorando mayusculas, diciendo
     cuales y con que ids (no un `Duplicate entry` sin contexto).
  2. Pasa a minusculas los correos y usuarios existentes, para que lo que hay
     en la base coincida con lo que normalizan los serializers.
  3. Cambia el UNIQUE de `email` por un indice FUNCIONAL sobre
     `LOWER(email)`, y anade otro sobre `LOWER(username)`.

Por que sobre la expresion y no sobre la columna: asi el indice tambien
sirve para BUSCAR. El login filtra con `Lower("email")`, y MySQL solo puede
usar un indice funcional cuando la expresion de la consulta coincide con la
del indice. `username` lleva el suyo porque es la columna contra la que
autentica `ModelBackend` (USERNAME_FIELD), asi que necesita la misma garantia.

Limitacion heredada de 0005 que NO cambia aqui: como `email` no admite NULL,
dos cuentas con `email=''` (p. ej. dos `createsuperuser` sin correo) siguen
chocando contra el indice unico. Es el comportamiento que ya habia; corregirlo
pide un `NULLIF` que dejaria la expresion fuera del alcance de las busquedas.
"""

from django.db import migrations

from cuentas.identidad import buscar, describir

INDICE_VIEJO = "uniq_auth_user_email"
INDICE_EMAIL = "uniq_auth_user_email_lower"
INDICE_USERNAME = "uniq_auth_user_username_lower"


def _existe(cursor, nombre: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() AND table_name = 'auth_user' "
        "AND index_name = %s",
        [nombre],
    )
    return cursor.fetchone()[0] > 0


def aplicar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        hallazgos = buscar(cursor)
        if hallazgos:
            raise RuntimeError(
                "No se puede aplicar la unicidad insensible a mayusculas: hay "
                "identidades repetidas en auth_user.\n"
                + describir(hallazgos)
                + "\n\nCon identidades repetidas el login no puede resolver a "
                "quien pertenece la sesion (elegia una cuenta arbitraria). "
                "Deja una sola cuenta por correo y por usuario antes de "
                "migrar. Para revisarlas sin migrar:\n"
                "  python manage.py verificar_emails_duplicados"
            )

        # La base tiene que quedar como la dejan los serializers, que ya
        # normalizan a minusculas: si no, una fila heredada en mayusculas
        # dejaria de encontrarse al autenticar bajo una collation sensible.
        cursor.execute("UPDATE auth_user SET email = LOWER(email) "
                       "WHERE email <> LOWER(email)")
        cursor.execute("UPDATE auth_user SET username = LOWER(username) "
                       "WHERE username <> LOWER(username)")

        if not _existe(cursor, INDICE_EMAIL):
            cursor.execute(
                f"ALTER TABLE `auth_user` ADD UNIQUE KEY `{INDICE_EMAIL}` "
                "((LOWER(`email`)))"
            )
        if not _existe(cursor, INDICE_USERNAME):
            cursor.execute(
                f"ALTER TABLE `auth_user` ADD UNIQUE KEY `{INDICE_USERNAME}` "
                "((LOWER(`username`)))"
            )
        # El UNIQUE plano de 0005 queda cubierto por el funcional, que ademas
        # es el unico que resiste una collation sensible a mayusculas.
        if _existe(cursor, INDICE_VIEJO):
            cursor.execute(f"ALTER TABLE `auth_user` DROP KEY `{INDICE_VIEJO}`")


def revertir(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        if not _existe(cursor, INDICE_VIEJO):
            cursor.execute(
                f"ALTER TABLE `auth_user` ADD UNIQUE KEY `{INDICE_VIEJO}` (`email`)"
            )
        for nombre in (INDICE_EMAIL, INDICE_USERNAME):
            if _existe(cursor, nombre):
                cursor.execute(f"ALTER TABLE `auth_user` DROP KEY `{nombre}`")


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0011_actividadusuario_actividad_usuario_fecha_idx"),
    ]

    operations = [
        migrations.RunPython(aplicar, revertir),
    ]
