from django.db import migrations
from django.utils.text import slugify

SLUG_LEN = 150


def _slug_unico(model, base):
    slug = base[:SLUG_LEN]
    contador = 2
    while model.objects.exclude(slug="").filter(slug=slug).exists():
        sufijo = f"-{contador}"
        slug = (base[:SLUG_LEN - len(sufijo)] + sufijo)
        contador += 1
    return slug


def backfill_slugs(apps, schema_editor):
    Empresa = apps.get_model("core", "Empresa")
    for empresa in Empresa.objects.filter(slug__isnull=True):
        base = slugify(empresa.nombre) or slugify(empresa.nit) or "empresa"
        empresa.slug = _slug_unico(Empresa, base)
        empresa.save(update_fields=["slug"])


def reverso(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_empresa_slug"),
    ]

    operations = [
        migrations.RunPython(backfill_slugs, reverso),
    ]
