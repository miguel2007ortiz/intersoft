"""Los comprobantes pasan a `DOCUMENTOS_ROOT`, fuera de `MEDIA_ROOT`.

No toca la base de datos: `storage` vive en el campo, no en la columna, y el
valor guardado sigue siendo la misma ruta relativa (`facturas/2026/09/pdf/...`).
Lo que cambia es la carpeta sobre la que se resuelve.

Por eso los archivos que ya estan en disco NO se mueven aqui: mover ficheros en
una migracion no se puede revertir si algo falla a mitad. Se mueven con
`python manage.py mover_documentos_privados`, que es idempotente y tiene
`--dry-run`. Hasta correrlo, los comprobantes viejos dan 410 al descargarse.
"""

import core.almacenamiento
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_recibo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facturaelectronica',
            name='pdf',
            field=models.FileField(blank=True, null=True, storage=core.almacenamiento.AlmacenamientoPrivado(), upload_to='facturas/%Y/%m/pdf/'),
        ),
        migrations.AlterField(
            model_name='facturaelectronica',
            name='xml',
            field=models.FileField(blank=True, null=True, storage=core.almacenamiento.AlmacenamientoPrivado(), upload_to='facturas/%Y/%m/xml/'),
        ),
        migrations.AlterField(
            model_name='notacredito',
            name='pdf',
            field=models.FileField(blank=True, null=True, storage=core.almacenamiento.AlmacenamientoPrivado(), upload_to='notas_credito/%Y/%m/pdf/'),
        ),
        migrations.AlterField(
            model_name='notacredito',
            name='xml',
            field=models.FileField(blank=True, null=True, storage=core.almacenamiento.AlmacenamientoPrivado(), upload_to='notas_credito/%Y/%m/xml/'),
        ),
        migrations.AlterField(
            model_name='recibo',
            name='archivo',
            field=models.FileField(blank=True, null=True, storage=core.almacenamiento.AlmacenamientoPrivado(), upload_to='recibos/%Y/%m/'),
        ),
    ]
