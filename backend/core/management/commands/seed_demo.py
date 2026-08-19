from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Empresa, Usuario, Categoria, Producto, Cliente, Venta
from cuentas.models import Perfil


class Command(BaseCommand):
    help = 'Carga datos de demostracion en la base de datos.'

    def handle(self, *args, **options):
        empresa, _ = Empresa.objects.get_or_create(
            nit='900123456',
            defaults={'nombre': 'Tienda El Progreso', 'email': 'contacto@elprogreso.co',
                      'telefono': '3001234567', 'plan': 'pro'})

        if not User.objects.filter(email='ana@elprogreso.co').exists():
            user = User.objects.create_user(
                username='ana@elprogreso.co', password='demo12345',
                first_name='Ana Torres', email='ana@elprogreso.co')
            Perfil.objects.create(usuario=user, empresa=empresa,
                                  rol='ADMINISTRADOR', es_propietario=True)

        usuarios_data = [('Ana Torres', 'ana@elprogreso.co', 'admin'),
                         ('Luis Perez', 'luis@elprogreso.co', 'vendedor')]
        usuarios = []
        for nombre, email, rol in usuarios_data:
            u, _ = Usuario.objects.get_or_create(
                empresa=empresa, email=email,
                defaults={'nombre': nombre, 'rol': rol, 'password_hash': 'demo'})
            usuarios.append(u)

        cat_calzado, _ = Categoria.objects.get_or_create(empresa=empresa, nombre='Calzado')
        cat_ropa, _ = Categoria.objects.get_or_create(empresa=empresa, nombre='Ropa')

        productos_data = [
            (cat_calzado, 'Zapatos deportivos', 'SKU-001', 75000, 40, 10),
            (cat_ropa, 'Medias deportivas', 'SKU-002', 12500, 200, 20),
            (cat_ropa, 'Camiseta Polo', 'SKU-003', 45000, 8, 10),      # stock bajo
            (cat_calzado, 'Sandalias', 'SKU-004', 35000, 5, 15),       # stock bajo
        ]
        for cat, nombre, sku, precio, stock, smin in productos_data:
            Producto.objects.get_or_create(
                empresa=empresa, sku=sku,
                defaults={'categoria': cat, 'nombre': nombre, 'precio': precio,
                          'stock': stock, 'stock_minimo': smin})

        clientes_data = [('Carlos Ramirez', 'CC', '1020304050', 'carlos@mail.co'),
                         ('Maria Gomez', 'CC', '1020304060', 'maria@mail.co')]
        clientes = []
        for nombre, tipo, num, email in clientes_data:
            c, _ = Cliente.objects.get_or_create(
                empresa=empresa, tipo_documento=tipo, numero_documento=num,
                defaults={'nombre': nombre, 'email': email})
            clientes.append(c)

        if not Venta.objects.filter(empresa=empresa).exists():
            Venta.objects.create(empresa=empresa, cliente=clientes[0], vendedor=usuarios[0],
                                 total=187500, estado='completada', metodo_pago='nequi')
            Venta.objects.create(empresa=empresa, cliente=clientes[1], vendedor=usuarios[1],
                                 total=90000, estado='completada', metodo_pago='efectivo')

        self.stdout.write(self.style.SUCCESS("¡Datos de demostracion cargados!"))
