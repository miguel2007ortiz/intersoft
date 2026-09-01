from django.core.management.base import BaseCommand

from core.models import Empresa
from cuentas.models import crear_roles_base


class Command(BaseCommand):
    help = ("Crea los roles ADMINISTRADOR, EMPLEADO y CLIENTE con sus permisos "
            "por defecto para cada empresa existente (idempotente).")

    def handle(self, *args, **options):
        empresas = Empresa.objects.all()
        for empresa in empresas:
            crear_roles_base(empresa)
        self.stdout.write(self.style.SUCCESS(
            f"Roles base listos para {len(empresas)} empresa(s)."))
