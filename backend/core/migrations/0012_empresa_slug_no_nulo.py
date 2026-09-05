from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_empresa_slug_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="empresa",
            name="slug",
            field=models.SlugField(blank=True, max_length=150, unique=True),
        ),
    ]
