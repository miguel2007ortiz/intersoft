"""Une las dos hojas del grafo de migraciones que quedaron al integrar las
ramas: `0019_grabacion` (catalogo de grabaciones de camaras) y
`0021_merge_0018_envio_0020_venta_intento_pago` (auditoria de pagos e
IntentoPago). No aplica operaciones: solo declara el punto de union para que
Django tenga una unica hoja y `migrate` pueda avanzar.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0019_grabacion'),
        ('core', '0021_merge_0018_envio_0020_venta_intento_pago'),
    ]

    operations = []
