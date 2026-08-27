from django.core.management.base import BaseCommand

from cuentas.models import Permiso, Rol, RolPermiso

# Catalogo base de permisos de la plataforma (codigo, descripcion)
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

# Permisos que recibe cada rol en la fase 1. CLIENTE no tiene todavia:
# su portal se construye en fases posteriores.
PERMISOS_POR_ROL = {
    "ADMINISTRADOR": [codigo for codigo, _ in PERMISOS_BASE],
    "EMPLEADO": ["productos.gestionar", "inventario.movimientos", "clientes.gestionar",
                 "ventas.gestionar", "reportes.ver"],
    "CLIENTE": [],
}


class Command(BaseCommand):
    help = "Crea los roles ADMINISTRADOR, EMPLEADO y CLIENTE con sus permisos."

    def handle(self, *args, **options):
        permisos = {}
        for codigo, descripcion in PERMISOS_BASE:
            permisos[codigo], _ = Permiso.objects.get_or_create(
                codigo=codigo, defaults={"descripcion": descripcion})

        for nombre_rol, codigos in PERMISOS_POR_ROL.items():
            rol, _ = Rol.objects.get_or_create(nombre=nombre_rol)
            for codigo in codigos:
                RolPermiso.objects.get_or_create(rol=rol, permiso=permisos[codigo])

        self.stdout.write(self.style.SUCCESS(
            "Roles listos: ADMINISTRADOR (todos los permisos), "
            f"EMPLEADO ({len(PERMISOS_POR_ROL['EMPLEADO'])} permisos), CLIENTE (ninguno por ahora)."))
