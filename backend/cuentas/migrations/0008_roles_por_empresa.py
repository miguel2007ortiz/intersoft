from django.db import migrations

ROLES_BASE = ["ADMINISTRADOR", "EMPLEADO", "CLIENTE"]


def crear_roles_por_empresa(apps, schema_editor):
    Empresa = apps.get_model("core", "Empresa")
    Rol = apps.get_model("cuentas", "Rol")
    RolPermiso = apps.get_model("cuentas", "RolPermiso")
    Perfil = apps.get_model("cuentas", "Perfil")

    roles_globales = list(Rol.objects.filter(empresa__isnull=True))
    permisos_por_rol = {}
    for rol in roles_globales:
        permisos_por_rol[rol.nombre] = list(rol.rol_permisos.values_list("permiso_id", flat=True))

    for empresa in Empresa.objects.all():
        roles_nuevos = {}
        for nombre in ROLES_BASE:
            rol, _ = Rol.objects.get_or_create(empresa=empresa, nombre=nombre)
            roles_nuevos[nombre] = rol
            for permiso_id in permisos_por_rol.get(nombre, []):
                RolPermiso.objects.get_or_create(rol=rol, permiso_id=permiso_id)

        for perfil in Perfil.objects.filter(empresa=empresa):
            nombre = perfil.rol.nombre if perfil.rol_id else None
            destino = roles_nuevos.get(nombre) or roles_nuevos["CLIENTE"]
            if perfil.rol_id != destino.pk:
                perfil.rol = destino
                perfil.save(update_fields=["rol"])

    Rol.objects.filter(empresa__isnull=True).delete()


def reverso(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0007_rol_empresa_alter_rol_nombre_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_roles_por_empresa, reverso),
    ]
