# Validacion global de fase 1: email unico de cuenta.
# El serializer ya lo valida en la API; este indice lo garantiza tambien a
# nivel de base de datos (defensa ante escrituras fuera del flujo DRF).
# Se usa SQL directo porque las migraciones de una app no pueden alterar
# el estado de los modelos de otra app (django.contrib.auth).
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0004_perfil_rol_fk"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE `auth_user` ADD UNIQUE KEY `uniq_auth_user_email` (`email`);",
            reverse_sql="ALTER TABLE `auth_user` DROP KEY `uniq_auth_user_email`;",
        ),
    ]
