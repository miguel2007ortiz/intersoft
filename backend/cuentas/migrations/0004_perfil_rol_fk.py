# Conversion segura de perfil.rol: de CharField a FK hacia cuentas.Rol.
# Se hace en pasos para conservar el dato de los perfiles existentes:
#   1) columna nueva rol_nuevo (FK, anulable)
#   2) se llena con el Rol que coincida con el texto antiguo
#   3) se borra la columna de texto y se renombra la nueva
from django.db import migrations, models
import django.db.models.deletion


def texto_a_fk(apps, schema_editor):
    Perfil = apps.get_model("cuentas", "Perfil")
    Rol = apps.get_model("cuentas", "Rol")
    for perfil in Perfil.objects.exclude(rol__isnull=True).exclude(rol=""):
        perfil.rol_nuevo = Rol.objects.get_or_create(nombre=perfil.rol)[0]
        perfil.save(update_fields=["rol_nuevo"])


def fk_a_texto(apps, schema_editor):
    Perfil = apps.get_model("cuentas", "Perfil")
    for perfil in Perfil.objects.exclude(rol_nuevo__isnull=True):
        perfil.rol = perfil.rol_nuevo.nombre
        perfil.save(update_fields=["rol"])


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0003_seed_rbac"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="rol_nuevo",
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="+", to="cuentas.rol"),
        ),
        migrations.RunPython(texto_a_fk, fk_a_texto),
        migrations.RemoveField(model_name="perfil", name="rol"),
        migrations.RenameField(model_name="perfil", old_name="rol_nuevo", new_name="rol"),
    ]
