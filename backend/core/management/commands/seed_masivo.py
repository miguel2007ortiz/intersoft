"""Genera un volumen grande de productos de prueba (con imagen y
descripcion) para probar el catalogo, el POS y el dashboard con datos
reales en desarrollo local. NO usar en produccion.

Uso:
    python manage.py seed_masivo
    python manage.py seed_masivo --cantidad 500
"""
import random

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from core.models import Categoria, Empresa, Producto

NIT_DEMO = '900123456'

CATEGORIAS = ['Electronica', 'Hogar', 'Ropa', 'Calzado', 'Alimentos',
              'Bebidas', 'Juguetes', 'Deportes', 'Belleza', 'Papeleria']

ADJETIVOS = ['Clasico', 'Premium', 'Basico', 'Deluxe', 'Compacto',
             'Portatil', 'Profesional', 'Economico', 'Resistente', 'Ligero']

SUSTANTIVOS_POR_CATEGORIA = {
    'Electronica': ['Audifonos', 'Cargador', 'Parlante', 'Mouse', 'Teclado'],
    'Hogar': ['Juego de ollas', 'Lampara', 'Cortina', 'Cojin', 'Organizador'],
    'Ropa': ['Camiseta', 'Pantalon', 'Chaqueta', 'Vestido', 'Sudadera'],
    'Calzado': ['Zapatos deportivos', 'Sandalias', 'Botas', 'Tenis', 'Zapatillas'],
    'Alimentos': ['Arroz', 'Pasta', 'Aceite', 'Enlatado', 'Snack'],
    'Bebidas': ['Gaseosa', 'Jugo', 'Agua', 'Cafe', 'Te'],
    'Juguetes': ['Muñeco', 'Rompecabezas', 'Carro de juguete', 'Peluche', 'Juego de mesa'],
    'Deportes': ['Balon', 'Guantes', 'Colchoneta', 'Pesas', 'Casco'],
    'Belleza': ['Crema', 'Shampoo', 'Perfume', 'Labial', 'Jabon'],
    'Papeleria': ['Cuaderno', 'Lapicero', 'Marcador', 'Carpeta', 'Resaltador'],
}

# Paleta de colores para las imagenes de relleno (una por categoria).
COLORES = {
    'Electronica': (52, 73, 94), 'Hogar': (155, 89, 182), 'Ropa': (231, 76, 60),
    'Calzado': (230, 126, 34), 'Alimentos': (39, 174, 96), 'Bebidas': (41, 128, 185),
    'Juguetes': (241, 196, 15), 'Deportes': (26, 188, 156), 'Belleza': (192, 57, 43),
    'Papeleria': (127, 140, 141),
}


def imagen_placeholder(texto: str, color: tuple) -> ContentFile:
    """Genera un PNG simple (fondo de color + texto) sin depender de
    archivos de fuente ni de internet."""
    img = Image.new('RGB', (400, 300), color=color)
    dibujo = ImageDraw.Draw(img)
    dibujo.rectangle([10, 10, 390, 290], outline=(255, 255, 255), width=3)
    dibujo.text((20, 140), texto[:28], fill=(255, 255, 255))
    buffer = ContentFile(b'')
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return ContentFile(buffer.read())


class Command(BaseCommand):
    help = 'Inserta productos de prueba en volumen (con imagen y descripcion).'

    def add_arguments(self, parser):
        parser.add_argument('--cantidad', type=int, default=1000)
        parser.add_argument('--nit', type=str, default=NIT_DEMO,
                            help='NIT de la empresa a poblar (por defecto la demo).')

    def handle(self, *args, **options):
        cantidad = options['cantidad']
        nit = options['nit']

        empresa = Empresa.objects.filter(nit=nit).first()
        if empresa is None:
            self.stdout.write('Empresa demo no encontrada, corriendo seed_demo primero...')
            call_command('seed_demo')
            empresa = Empresa.objects.get(nit=nit)

        categorias = {}
        for nombre in CATEGORIAS:
            cat, _ = Categoria.objects.get_or_create(
                empresa=empresa, nombre=nombre,
                defaults={'descripcion': f'Categoria de {nombre.lower()} de prueba.'})
            categorias[nombre] = cat

        # Una sola imagen fisica por categoria (no 1000 archivos): se
        # escribe una vez a disco y los productos solo apuntan su `imagen`
        # a esa misma ruta relativa.
        ruta_imagen_por_categoria = {}
        for nombre in CATEGORIAS:
            ruta = f'productos/demo/{nombre.lower()}.png'
            if not default_storage.exists(ruta):
                default_storage.save(ruta, imagen_placeholder(nombre, COLORES[nombre]))
            ruta_imagen_por_categoria[nombre] = ruta

        existentes = set(Producto.objects.filter(empresa=empresa)
                          .values_list('sku', flat=True))
        siguiente = 1
        nuevos = []
        creados = 0
        while creados < cantidad:
            sku = f'DEMO-{siguiente:05d}'
            siguiente += 1
            if sku in existentes:
                continue

            categoria_nombre = random.choice(CATEGORIAS)
            categoria = categorias[categoria_nombre]
            adjetivo = random.choice(ADJETIVOS)
            sustantivo = random.choice(SUSTANTIVOS_POR_CATEGORIA[categoria_nombre])
            nombre = f'{sustantivo} {adjetivo} #{siguiente}'
            precio = random.randint(5, 800) * 1000
            stock = random.randint(0, 150)
            stock_minimo = random.randint(5, 30)
            descripcion = (
                f'{sustantivo} {adjetivo.lower()} de la categoria {categoria_nombre}. '
                f'Producto de prueba generado para validar catalogo, POS e inventario '
                f'con datos de volumen.'
            )

            producto = Producto(
                empresa=empresa, categoria=categoria, nombre=nombre, sku=sku,
                descripcion=descripcion, precio=precio, stock=stock,
                stock_minimo=stock_minimo, activo=True,
            )
            producto.imagen.name = ruta_imagen_por_categoria[categoria_nombre]
            nuevos.append(producto)
            creados += 1

            # bulk_create en lotes: evita 1000 INSERTs individuales y no
            # dispara signals (post_save de alerta de stock bajo).
            if len(nuevos) >= 200:
                Producto.objects.bulk_create(nuevos)
                nuevos = []

        if nuevos:
            Producto.objects.bulk_create(nuevos)

        self.stdout.write(self.style.SUCCESS(
            f'{creados} productos de prueba creados en "{empresa.nombre}" '
            f'({len(CATEGORIAS)} categorias, con imagen y descripcion).'
        ))
