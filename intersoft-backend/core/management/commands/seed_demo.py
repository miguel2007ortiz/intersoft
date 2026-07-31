"""
Comando personalizado: carga datos de demostración.

Uso:
    python manage.py seed_demo

Crea una empresa con usuarios, categorías, productos, clientes y ventas
para que el dashboard tenga información desde el primer arranque.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Empresa, Usuario, Categoria, Producto, Cliente, Venta, Perfil


class Command(BaseCommand):
    help = 'Carga datos de demostración en la base de datos.'

    def handle(self, *args, **options):
        self.stdout.write("Cargando datos de demostración...")

        # ── Empresa ──────────────────────────────────────────
        empresa, _ = Empresa.objects.get_or_create(
            nit='900123456',
            defaults={
                'nombre': 'Tienda El Progreso',
                'email': 'contacto@elprogreso.co',
                'telefono': '3001234567',
                'plan': 'pro',
            }
        )
        self.stdout.write(self.style.SUCCESS(f"  ✓ Empresa: {empresa.nombre}"))

        # ── Cuenta de acceso demo (login) ────────────────────
        if not User.objects.filter(username='demo').exists():
            user = User.objects.create_user(
                username='demo', password='demo12345',
                first_name='Ana Torres', email='ana@elprogreso.co'
            )
            Perfil.objects.create(user=user, empresa=empresa, es_propietario=True)
            self.stdout.write(self.style.SUCCESS("  ✓ Login demo → usuario: demo / clave: demo12345"))

        # ── Usuarios ─────────────────────────────────────────
        usuarios_data = [
            ('Ana Torres', 'ana@elprogreso.co', 'admin'),
            ('Luis Pérez', 'luis@elprogreso.co', 'vendedor'),
        ]
        usuarios = []
        for nombre, email, rol in usuarios_data:
            u, _ = Usuario.objects.get_or_create(
                empresa=empresa, email=email,
                defaults={'nombre': nombre, 'rol': rol, 'password_hash': 'demo'}
            )
            usuarios.append(u)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(usuarios)} usuarios"))

        # ── Categorías ───────────────────────────────────────
        cat_calzado, _ = Categoria.objects.get_or_create(empresa=empresa, nombre='Calzado')
        cat_ropa, _ = Categoria.objects.get_or_create(empresa=empresa, nombre='Ropa')

        # ── Productos ────────────────────────────────────────
        productos_data = [
            (cat_calzado, 'Zapatos deportivos', 'SKU-001', 75000, 40, 10),
            (cat_ropa, 'Medias deportivas', 'SKU-002', 12500, 200, 20),
            (cat_ropa, 'Camiseta Polo', 'SKU-003', 45000, 8, 10),  # stock bajo a propósito
            (cat_calzado, 'Sandalias', 'SKU-004', 35000, 5, 15),   # stock bajo
        ]
        for cat, nombre, sku, precio, stock, smin in productos_data:
            Producto.objects.get_or_create(
                empresa=empresa, sku=sku,
                defaults={
                    'categoria': cat, 'nombre': nombre, 'precio': precio,
                    'stock': stock, 'stock_minimo': smin,
                }
            )
        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(productos_data)} productos"))

        # ── Clientes ─────────────────────────────────────────
        clientes_data = [
            ('Carlos Ramírez', 'CC', '1020304050', 'carlos@mail.co'),
            ('María Gómez', 'CC', '1020304060', 'maria@mail.co'),
        ]
        clientes = []
        for nombre, tipo, num, email in clientes_data:
            c, _ = Cliente.objects.get_or_create(
                empresa=empresa, tipo_documento=tipo, numero_documento=num,
                defaults={'nombre': nombre, 'email': email}
            )
            clientes.append(c)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(clientes)} clientes"))

        # ── Ventas ───────────────────────────────────────────
        if not Venta.objects.filter(empresa=empresa).exists():
            Venta.objects.create(
                empresa=empresa, cliente=clientes[0], vendedor=usuarios[0],
                total=187500, estado='completada', metodo_pago='nequi'
            )
            Venta.objects.create(
                empresa=empresa, cliente=clientes[1], vendedor=usuarios[1],
                total=90000, estado='completada', metodo_pago='efectivo'
            )
            self.stdout.write(self.style.SUCCESS("  ✓ 2 ventas"))

        self.stdout.write(self.style.SUCCESS("\n¡Datos de demostración cargados!"))
        self.stdout.write("Abre http://localhost:8000/ para ver el dashboard.")
