# La FK rol quedo anulable tras el renombrado de la 0004; el modelo la
# declara obligatoria. Todas las filas ya tienen rol asignado por la
# conversion, asi que basta con alterar la columna.
import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0005_email_usuario_unico"),
    ]

    operations = [
        migrations.AlterField(
            model_name="perfil",
            name="rol",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                    related_name="perfiles", to="cuentas.rol"),
        ),
    ]
