from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (Carrito, CarritoItem, Categoria, Cliente, DetalleVenta,
                         Empresa, Favorito, Producto, Venta)
from cuentas.models import Perfil, Rol

from .seed_masivo import imagen_placeholder

# Paleta unica para cada categoria de la tienda demo (Textura visual de las
# imagenes de producto del catalogo publico).
COLORES = {
    'Calzado': (230, 126, 34),
    'Ropa': (231, 76, 60),
}


def _rol(nombre):
    """Obtiene un rol base por nombre sin crear duplicados (el ambiente
    puede tener roles repetidos de seeds previos)."""
    return Rol.objects.filter(nombre=nombre).first()


class Command(BaseCommand):
    help = 'Carga datos de demostracion en la base de datos.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Ejecuta el seed incluso con DEBUG=False.')

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'seed_demo solo debe ejecutarse en desarrollo (DEBUG=True). '
                'Usa --force si entiendes los riesgos.')
        empresa, _ = Empresa.objects.get_or_create(
            nit='900123456',
            defaults={'nombre': 'Tienda El Progreso', 'email': 'contacto@elprogreso.co',
                      'telefono': '3001234567', 'plan': 'pro'})

        # --- Comprador demo (rol CLIENTE) con historial real.
        if not User.objects.filter(email='ana@elprogreso.co').exists():
            user = User.objects.create_user(
                username='ana@elprogreso.co', password='demo12345',
                first_name='Ana Torres', email='ana@elprogreso.co')
            Perfil.objects.create(usuario=user, empresa=empresa,
                                  rol=_rol('CLIENTE'),
                                  es_propietario=True)
        ana = User.objects.get(email='ana@elprogreso.co')

        # Personal de la tienda (para las ventas del historial).
        cuentas_data = [('Ana Torres', 'ana@elprogreso.co'),
                        ('Luis Perez', 'luis@elprogreso.co')]
        usuarios = []
        for nombre, email in cuentas_data:
            user, _ = User.objects.get_or_create(
                username=email,
                defaults={'first_name': nombre.split(' ', 1)[0],
                          'last_name': nombre.split(' ', 1)[1] if ' ' in nombre else '',
                          'email': email})
            perfil, _ = Perfil.objects.get_or_create(
                usuario=user,
                defaults={'empresa': empresa, 'rol': _rol('EMPLEADO')})
            usuarios.append(user)

        cat_calzado, _ = Categoria.objects.get_or_create(empresa=empresa, nombre='Calzado')
        cat_ropa, _ = Categoria.objects.get_or_create(empresa=empresa, nombre='Ropa')

        productos_data = [
            (cat_calzado, 'Zapatos deportivos', 'SKU-001', 75000, 40, 10),
            (cat_ropa, 'Medias deportivas', 'SKU-002', 12500, 200, 20),
            (cat_ropa, 'Camiseta Polo', 'SKU-003', 45000, 8, 10),      # stock bajo
            (cat_calzado, 'Sandalias', 'SKU-004', 35000, 5, 15),       # stock bajo
        ]
        # Imagen placeholder por categoria (una fisica por categoria).
        ruta_por_cat = {}
        for cat_obj, nombre, sku, precio, stock, smin in productos_data:
            cat_nombre = cat_obj.nombre
            if cat_nombre not in ruta_por_cat:
                ruta = f'productos/demo/{cat_nombre.lower()}.png'
                if not default_storage.exists(ruta):
                    default_storage.save(ruta, imagen_placeholder(cat_nombre,
                                                                  COLORES[cat_nombre]))
                ruta_por_cat[cat_nombre] = ruta
            Producto.objects.get_or_create(
                empresa=empresa, sku=sku,
                defaults={'categoria': cat_obj, 'nombre': nombre, 'precio': precio,
                          'stock': stock, 'stock_minimo': smin, 'imagen': ruta})

        clientes_data = [('Carlos Ramirez', 'CC', '1020304050', 'carlos@mail.co'),
                         ('Maria Gomez', 'CC', '1020304060', 'maria@mail.co')]
        clientes = []
        for nombre, tipo, num, email in clientes_data:
            c, _ = Cliente.objects.get_or_create(
                empresa=empresa, tipo_documento=tipo, numero_documento=num,
                defaults={'nombre': nombre, 'email': email})
            clientes.append(c)

        # Cliente vinculado a Ana (para su historial de pedidos).
        cliente_ana, _ = Cliente.objects.get_or_create(
            usuario=ana,
            defaults={'empresa': empresa, 'nombre': 'Ana Torres',
                      'tipo_documento': 'CC', 'numero_documento': '99990001122',
                      'email': ana.email})

        # --- Pedidos demo normalizados (los totales se recalculan por senal).
        p_zapatos = Producto.objects.get(empresa=empresa, sku='SKU-001')
        p_camiseta = Producto.objects.get(empresa=empresa, sku='SKU-003')
        p_sandalias = Producto.objects.get(empresa=empresa, sku='SKU-004')

        def normalizar_venta(numero_factura, metodo_pago, lineas):
            venta, _ = Venta.objects.get_or_create(
                empresa=empresa, numero_factura=numero_factura,
                defaults={'cliente': cliente_ana, 'vendedor': usuarios[0],
                          'fecha': timezone.now(), 'metodo_pago': metodo_pago})
            venta.cliente = cliente_ana
            venta.vendedor = usuarios[0]
            venta.estado = 'completada'
            venta.metodo_pago = metodo_pago
            if not venta.fecha:
                venta.fecha = timezone.now()
            venta.save()
            if not DetalleVenta.objects.filter(venta=venta).exists():
                for producto, cantidad, precio in lineas:
                    DetalleVenta.objects.create(venta=venta, producto=producto,
                                                cantidad=cantidad,
                                                precio_unitario=precio)

        normalizar_venta('FT-00001', 'nequi', [(p_zapatos, 1, 75000)])
        normalizar_venta('FT-00002', 'efectivo',
                         [(p_camiseta, 2, 45000), (p_sandalias, 1, 35000)])

        # --- Favoritos de Ana (aparecen en la pantalla de favoritos).
        Favorito.objects.get_or_create(usuario=ana, producto=p_camiseta)
        Favorito.objects.get_or_create(usuario=ana, producto=p_zapatos)

        # --- Carrito de Ana (2 items para la vista de carrito/checkout).
        carrito, _ = Carrito.objects.get_or_create(usuario=ana)
        carrito.empresa = empresa
        carrito.save()
        CarritoItem.objects.get_or_create(carrito=carrito, producto=p_camiseta,
                                          defaults={'cantidad': 2})
        CarritoItem.objects.get_or_create(carrito=carrito, producto=p_zapatos,
                                          defaults={'cantidad': 1})

        self.stdout.write(self.style.SUCCESS("¡Datos de demostracion cargados!"))