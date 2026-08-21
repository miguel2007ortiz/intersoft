# Semilla de datos RBAC (fase 1): roles base y su catalogo de permisos.
from django.db import migrations

ROLES = [
    ("ADMINISTRADOR", "Control total de la empresa"),
    ("EMPLEADO", "Operacion diaria: productos, inventario, clientes y ventas"),
    ("CLIENTE", "Comprador del portal de la empresa"),
]

PERMISOS_BASE = [
    ("usuarios.gestionar", "Crear, editar y desactivar cuentas de la empresa"),
    ("roles.asignar", "Asignar roles y permisos a los usuarios"),
    ("productos.gestionar", "Crear, editar y desactivar productos"),
    ("inventario.movimientos", "Registrar entradas, salidas y ajustes de stock"),
    ("clientes.gestionar", "Administrar el directorio de clientes"),
    ("ventas.gestionar", "Registrar, completar y anular ventas"),
    ("reportes.ver", "Consultar reportes e indicadores"),
    ("configuracion.gestionar", "Editar los datos de la empresa"),
]

PERMISOS_POR_ROL = {
    "ADMINISTRADOR": [codigo for codigo, _ in PERMISOS_BASE],
    "EMPLEADO": ["productos.gestionar", "inventario.movimientos", "clientes.gestionar",
                 "ventas.gestionar", "reportes.ver"],
    "CLIENTE": [],
}


def sembrar(apps, schema_editor):
    Permiso = apps.get_model("cuentas", "Permiso")
    Rol = apps.get_model("cuentas", "Rol")
    RolPermiso = apps.get_model("cuentas", "RolPermiso")

    permisos = {}
    for codigo, descripcion in PERMISOS_BASE:
        permisos[codigo], _ = Permiso.objects.get_or_create(
            codigo=codigo, defaults={"descripcion": descripcion})

    roles = {}
    for nombre, descripcion in ROLES:
        roles[nombre], _ = Rol.objects.get_or_create(
            nombre=nombre, defaults={"descripcion": descripcion})
        for codigo in PERMISOS_POR_ROL[nombre]:
            RolPermiso.objects.get_or_create(rol=roles[nombre], permiso=permisos[codigo])


def borrar(apps, schema_editor):
    RolPermiso = apps.get_model("cuentas", "RolPermiso")
    Rol = apps.get_model("cuentas", "Rol")
    Permiso = apps.get_model("cuentas", "Permiso")
    RolPermiso.objects.all().delete()
    Rol.objects.filter(nombre__in=[r for r, _ in ROLES]).delete()
    Permiso.objects.filter(codigo__in=[c for c, _ in PERMISOS_BASE]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0002_permiso_rol_actividadusuario_alter_perfil_rol_and_more"),
    ]

    operations = [
        migrations.RunPython(sembrar, borrar),
    ]
