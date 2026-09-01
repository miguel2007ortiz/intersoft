import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0008_roles_por_empresa"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rol",
            name="empresa",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="roles",
                to="core.empresa",
            ),
        ),
    ]
