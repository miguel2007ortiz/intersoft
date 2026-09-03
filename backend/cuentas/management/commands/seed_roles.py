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

# Permisos finos (fase Empleados). Aditivos: no reemplazan los gruesos de
# arriba, que siguen sin usarse en ningun permission class real salvo donde
# se indique. Estos si se consultan desde el codigo (ver cuentas/permissions.py).
PERMISOS_FINOS_BASE = [
    ("empleado.crear", "Crear cuentas de personal (Empleado/Administrador)"),
    ("empleado.leer", "Ver el listado y detalle de personal"),
    ("empleado.actualizar", "Editar datos laborales y rol del personal"),
    ("empleado.desactivar", "Desactivar o reactivar cuentas de personal"),
    ("producto.crear", "Crear productos del catalogo"),
    ("producto.leer", "Ver el catalogo de productos"),
    ("producto.actualizar", "Editar productos, incluido el precio"),
    ("producto.desactivar", "Desactivar o reactivar productos"),
    ("venta.crear", "Registrar ventas"),
    ("venta.leer_propias", "Ver unicamente las ventas registradas por si mismo"),
    ("venta.leer_todas", "Ver todas las ventas de la empresa"),
]

# Solo ADMINISTRADOR gestiona personal y precios; EMPLEADO ve el catalogo y
# solo sus propias ventas (RN de la matriz de permisos de Empleados).
PERMISOS_FINOS_POR_ROL = {
    "ADMINISTRADOR": [codigo for codigo, _ in PERMISOS_FINOS_BASE],
    "EMPLEADO": ["producto.leer", "venta.crear", "venta.leer_propias"],
    "CLIENTE": [],
}


class Command(BaseCommand):
    help = "Crea los roles ADMINISTRADOR, EMPLEADO y CLIENTE con sus permisos."

    def handle(self, *args, **options):
        permisos = {}
        for codigo, descripcion in PERMISOS_BASE + PERMISOS_FINOS_BASE:
            permisos[codigo], _ = Permiso.objects.get_or_create(
                codigo=codigo, defaults={"descripcion": descripcion})

        for nombre_rol, codigos in PERMISOS_POR_ROL.items():
            rol, _ = Rol.objects.get_or_create(nombre=nombre_rol)
            for codigo in codigos:
                RolPermiso.objects.get_or_create(rol=rol, permiso=permisos[codigo])

        for nombre_rol, codigos in PERMISOS_FINOS_POR_ROL.items():
            rol, _ = Rol.objects.get_or_create(nombre=nombre_rol)
            for codigo in codigos:
                RolPermiso.objects.get_or_create(rol=rol, permiso=permisos[codigo])

        self.stdout.write(self.style.SUCCESS(
            "Roles listos: ADMINISTRADOR (todos los permisos), "
            f"EMPLEADO ({len(PERMISOS_POR_ROL['EMPLEADO'])} gruesos + "
            f"{len(PERMISOS_FINOS_POR_ROL['EMPLEADO'])} finos), CLIENTE (ninguno por ahora)."))
