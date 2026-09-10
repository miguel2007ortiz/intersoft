"""Reemplaza las imagenes de relleno de los productos de demostracion por
fotos reales descargadas de Wikimedia Commons.

`seed_masivo` deja un PNG de color plano por categoria, asi que las 1000
fichas del catalogo se ven identicas. Este comando baja fotos de verdad,
una busqueda por cada sustantivo del generador de nombres, de modo que
"Aceite Basico #541" muestre una botella de aceite y no un rectangulo verde.

Fuente: la API publica de Wikimedia Commons (contenido libre, sin llave de
API). Requiere internet; solo para desarrollo local.

Uso:
    python manage.py imagenes_reales
    python manage.py imagenes_reales --por-termino 5
    python manage.py imagenes_reales --forzar     # vuelve a descargar
"""
import json
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Producto

API_COMMONS = 'https://commons.wikimedia.org/w/api.php'
# Commons pide un User-Agent que identifique a quien llama.
AGENTE = 'intersoft-demo/1.0 (desarrollo local; imagenes de catalogo)'
CARPETA = 'productos/reales'
# Wikimedia solo tiene cacheados unos anchos concretos; pedir uno distinto
# la obliga a generar la miniatura al vuelo y responde 429. 640 es uno de los
# suyos, y de paso el archivo pesa menos.
ANCHO = 640
TIEMPO_ESPERA = 30
# Aun asi responde 429 si se le piden decenas de imagenes seguidas, asi que
# se espera entre llamadas y se reintenta con pausas cada vez mas largas.
PAUSA_ENTRE_LLAMADAS = 2.0
REINTENTOS = 4

# Sustantivo con el que `seed_masivo` arma el nombre -> (busqueda en ingles,
# palabras que deben aparecer en el titulo del archivo).
#
# El buscador de Commons es de texto libre sobre la descripcion, asi que
# "soccer ball" tambien devuelve fotos de estadios llenos y "lipstick" saca
# retratos. Exigir el sustantivo en el titulo del archivo deja pasar solo las
# fotos que de verdad son del objeto.
BUSQUEDAS = {
    'Audifonos': ('headphones', ('headphone', 'headset', 'earphone')),
    'Cargador': ('usb charger', ('charger',)),
    'Parlante': ('bluetooth speaker', ('speaker',)),
    'Mouse': ('computer mouse', ('mouse',)),
    'Teclado': ('computer keyboard', ('keyboard',)),
    'Juego de ollas': ('cooking pot', ('pot', 'pan', 'cookware')),
    'Lampara': ('table lamp', ('lamp',)),
    'Cortina': ('window curtain', ('curtain',)),
    'Cojin': ('throw pillow cushion', ('cushion', 'pillow')),
    'Organizador': ('storage box organizer', ('box', 'organizer', 'storage')),
    'Camiseta': ('t-shirt', ('shirt', 'tshirt', 't-shirt')),
    'Pantalon': ('trousers', ('trouser', 'pants', 'jeans')),
    'Chaqueta': ('jacket', ('jacket',)),
    'Vestido': ('dress clothing', ('dress',)),
    'Sudadera': ('hoodie sweatshirt', ('hoodie', 'sweatshirt')),
    'Zapatos deportivos': ('sport shoes', ('shoe', 'trainer')),
    'Sandalias': ('sandals', ('sandal',)),
    'Botas': ('leather boots', ('boot',)),
    'Tenis': ('sneakers', ('sneaker', 'shoe')),
    'Zapatillas': ('running shoes', ('shoe', 'sneaker')),
    'Arroz': ('rice bowl', ('rice',)),
    'Pasta': ('pasta food', ('pasta', 'spaghetti', 'macaroni')),
    'Aceite': ('olive oil bottle', ('oil',)),
    'Enlatado': ('canned food tin', ('can', 'tin')),
    'Snack': ('potato chips snack', ('chips', 'snack', 'crisps')),
    'Gaseosa': ('soft drink bottle', ('soda', 'cola', 'soft drink')),
    'Jugo': ('orange juice glass', ('juice',)),
    'Agua': ('bottled water', ('water',)),
    'Cafe': ('coffee cup', ('coffee',)),
    'Te': ('tea cup', ('tea',)),
    'Muñeco': ('action figure toy', ('figure', 'doll', 'toy')),
    'Rompecabezas': ('jigsaw puzzle', ('puzzle',)),
    'Carro de juguete': ('toy car', ('toy car', 'model car', 'diecast')),
    'Peluche': ('teddy bear plush', ('teddy', 'plush', 'stuffed')),
    'Juego de mesa': ('board game', ('board game', 'boardgame')),
    'Balon': ('football ball', ('ball',)),
    'Guantes': ('boxing gloves', ('glove',)),
    'Colchoneta': ('yoga mat', ('mat',)),
    'Pesas': ('dumbbell', ('dumbbell', 'weight')),
    'Casco': ('bicycle helmet', ('helmet',)),
    'Crema': ('face cream jar', ('cream',)),
    'Shampoo': ('shampoo bottle', ('shampoo',)),
    'Perfume': ('perfume bottle', ('perfume',)),
    'Labial': ('lipstick', ('lipstick',)),
    'Jabon': ('soap bar', ('soap',)),
    'Cuaderno': ('notebook paper', ('notebook',)),
    'Lapicero': ('ballpoint pen', ('pen',)),
    'Marcador': ('marker pen', ('marker',)),
    'Carpeta': ('file folder', ('folder',)),
    'Resaltador': ('highlighter pen', ('highlighter',)),
}

# Titulos que casi nunca corresponden a una foto de producto.
TITULOS_DESCARTADOS = ('logo', 'map', 'diagram', 'chart', 'graph', 'poster',
                       'stamp', 'coat of arms', 'flag', 'icon')

# Categorias de Commons por sustantivo. Son listas curadas por personas, asi
# que dan muchos menos falsos positivos que el buscador de texto: buscar
# "lipstick" devuelve retratos y "crema" saca ceramica de un pueblo italiano,
# mientras que Category:Lipsticks solo tiene labiales.
#
# Se prueban en orden y se usa la primera que devuelva suficientes fotos; si
# ninguna sirve se cae a la busqueda de texto de BUSQUEDAS.
CATEGORIAS_COMMONS = {
    'Audifonos': ('Headphones',),
    'Cargador': ('Battery chargers', 'AC adapters'),
    'Parlante': ('Loudspeakers', 'Portable loudspeakers'),
    'Mouse': ('Computer mice',),
    'Teclado': ('Computer keyboards',),
    'Juego de ollas': ('Cooking pots', 'Cookware'),
    'Lampara': ('Table lamps', 'Lamps'),
    'Cortina': ('Curtains',),
    'Cojin': ('Cushions', 'Pillows'),
    'Organizador': ('Storage boxes', 'Boxes'),
    'Camiseta': ('T-shirts',),
    'Pantalon': ('Trousers', 'Jeans'),
    'Chaqueta': ('Jackets',),
    'Vestido': ('Dresses',),
    'Sudadera': ('Sweatshirts', 'Hoodies'),
    'Zapatos deportivos': ('Sports shoes', 'Athletic shoes'),
    'Sandalias': ('Sandals',),
    'Botas': ('Boots',),
    'Tenis': ('Sneakers', 'Athletic shoes'),
    'Zapatillas': ('Running shoes', 'Sports shoes'),
    'Arroz': ('Rice', 'Cooked rice'),
    'Pasta': ('Pasta', 'Spaghetti'),
    'Aceite': ('Olive oil', 'Cooking oil'),
    'Enlatado': ('Canned food', 'Food cans'),
    'Snack': ('Potato chips', 'Snack food'),
    'Gaseosa': ('Soft drink bottles', 'Soft drinks'),
    'Jugo': ('Fruit juices', 'Orange juice'),
    'Agua': ('Water bottles', 'Bottled water'),
    'Cafe': ('Cups of coffee', 'Coffee'),
    'Te': ('Cups of tea', 'Tea'),
    'Muñeco': ('Action figures', 'Dolls'),
    'Rompecabezas': ('Jigsaw puzzles',),
    'Carro de juguete': ('Toy cars', 'Model cars'),
    'Peluche': ('Teddy bears', 'Stuffed toys'),
    'Juego de mesa': ('Board games',),
    'Balon': ('Footballs (balls)', 'Balls'),
    'Guantes': ('Boxing gloves', 'Gloves'),
    'Colchoneta': ('Exercise mats', 'Yoga mats'),
    'Pesas': ('Dumbbells',),
    'Casco': ('Bicycle helmets', 'Helmets'),
    'Crema': ('Cosmetic creams', 'Skin care products'),
    'Shampoo': ('Shampoo', 'Shampoo bottles'),
    'Perfume': ('Perfume bottles', 'Perfumes'),
    'Labial': ('Lipsticks',),
    'Jabon': ('Soap', 'Bar soap'),
    'Cuaderno': ('Notebooks', 'Exercise books'),
    'Lapicero': ('Ballpoint pens', 'Pens'),
    'Marcador': ('Marker pens', 'Markers'),
    'Carpeta': ('File folders', 'Ring binders'),
    'Resaltador': ('Highlighters', 'Marker pens'),
}

# Los sustantivos largos van primero: "Juego de mesa" debe ganarle a "Juego
# de ollas" y ninguno debe partirse por la primera palabra.
SUSTANTIVOS = sorted(BUSQUEDAS, key=len, reverse=True)


def sin_tildes(texto: str) -> str:
    """'Muneco' sin la enye, para armar nombres de archivo seguros."""
    normal = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in normal if not unicodedata.combining(c))


def a_slug(texto: str) -> str:
    return sin_tildes(texto).lower().replace(' ', '-')


def abrir(url: str) -> bytes:
    """GET con espera entre llamadas y reintento ante 429/503."""
    peticion = urllib.request.Request(url, headers={'User-Agent': AGENTE})
    for intento in range(REINTENTOS):
        time.sleep(PAUSA_ENTRE_LLAMADAS)
        try:
            with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as respuesta:
                return respuesta.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503) or intento == REINTENTOS - 1:
                raise
            # 2s, 6s, 14s: le da aire al servidor antes de volver a pedir.
            time.sleep(2 ** (intento + 1) + intento * 2)
    raise OSError('sin respuesta tras varios reintentos')


def pedir_json(parametros: dict) -> dict:
    url = f'{API_COMMONS}?{urllib.parse.urlencode(parametros)}'
    return json.loads(abrir(url).decode('utf-8'))


def urls_utiles(paginas: dict, cantidad: int, claves: tuple = ()) -> list:
    """Filtra los resultados de la API y devuelve URLs de miniatura.

    Con `claves` ademas exige que el titulo nombre el objeto; desde una
    categoria curada eso sobra, porque la lista ya viene revisada."""
    # La API devuelve las paginas sin orden; `index` conserva el ranking.
    ordenadas = sorted(paginas.values(), key=lambda p: p.get('index', 999))
    urls = []
    for pagina in ordenadas:
        info = (pagina.get('imageinfo') or [{}])[0]
        if info.get('mime') not in ('image/jpeg', 'image/png'):
            continue
        if not info.get('thumburl'):
            continue
        # 'File:Red running shoes.jpg' -> 'Red running shoes.jpg'
        titulo = pagina.get('title', '').removeprefix('File:')
        limpio = sin_tildes(titulo).lower()
        if any(descarte in limpio for descarte in TITULOS_DESCARTADOS):
            continue
        if claves and not any(clave in limpio for clave in claves):
            continue
        urls.append(info['thumburl'])
        if len(urls) == cantidad:
            break
    return urls


def fotos_de_categoria(categoria: str, cantidad: int) -> list:
    """Fotos tomadas directamente de una categoria de Commons."""
    datos = pedir_json({
        'action': 'query', 'format': 'json', 'generator': 'categorymembers',
        'gcmtitle': f'Category:{categoria}',
        'gcmtype': 'file',
        # De sobra: muchas entradas son SVG o no traen miniatura.
        'gcmlimit': 60,
        'prop': 'imageinfo', 'iiprop': 'url|mime', 'iiurlwidth': ANCHO,
    })
    return urls_utiles(datos.get('query', {}).get('pages', {}), cantidad)


def buscar_fotos(termino: str, claves: tuple, cantidad: int) -> list:
    """Devuelve URLs de miniaturas de Commons para el termino dado.

    `filetype:bitmap` deja fuera los SVG (logos y diagramas, no fotos) y
    `gsrnamespace=6` restringe la busqueda a paginas de archivo."""
    datos = pedir_json({
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': f'filetype:bitmap {termino}',
        'gsrnamespace': 6,
        # Se pide de sobra porque el filtro por titulo descarta bastantes.
        'gsrlimit': 40,
        'prop': 'imageinfo', 'iiprop': 'url|mime', 'iiurlwidth': ANCHO,
    })
    return urls_utiles(datos.get('query', {}).get('pages', {}), cantidad, claves)


def descargar(url: str) -> bytes:
    return abrir(url)


class Command(BaseCommand):
    help = 'Descarga fotos reales de Wikimedia Commons para los productos demo.'

    def add_arguments(self, parser):
        parser.add_argument('--por-termino', type=int, default=3,
                            help='Fotos distintas por tipo de producto (def. 3).')
        parser.add_argument('--forzar', action='store_true',
                            help='Vuelve a descargar aunque el archivo ya exista.')

    def handle(self, *args, **opciones):
        por_termino = opciones['por_termino']
        forzar = opciones['forzar']

        rutas_por_sustantivo = self._descargar_todo(por_termino, forzar)
        if not rutas_por_sustantivo:
            self.stderr.write(self.style.ERROR(
                'No se pudo descargar ninguna imagen. Revisa la conexion.'))
            return
        self._asignar(rutas_por_sustantivo)

    def _descargar_todo(self, por_termino: int, forzar: bool) -> dict:
        rutas_por_sustantivo: dict[str, list[str]] = {}
        for sustantivo, (termino, claves) in BUSQUEDAS.items():
            slug = a_slug(sustantivo)
            rutas = []
            # Si ya estan en disco no se vuelve a llamar a la API.
            if not forzar:
                rutas = [f'{CARPETA}/{slug}-{i}.jpg' for i in range(por_termino)
                         if default_storage.exists(f'{CARPETA}/{slug}-{i}.jpg')]
            if len(rutas) < por_termino:
                rutas = self._descargar_termino(
                    sustantivo, slug, termino, claves, por_termino)
            if rutas:
                rutas_por_sustantivo[sustantivo] = rutas
                self.stdout.write(f'  {sustantivo:20} {len(rutas)} foto(s)')
            else:
                self.stderr.write(self.style.WARNING(
                    f'  {sustantivo:20} sin resultados ("{termino}")'))
        return rutas_por_sustantivo

    def _descargar_termino(self, sustantivo: str, slug: str, termino: str,
                           claves: tuple, cantidad: int) -> list:
        urls = self._urls_para(sustantivo, termino, claves, cantidad)
        rutas = []
        for indice, url in enumerate(urls):
            ruta = f'{CARPETA}/{slug}-{indice}.jpg'
            try:
                contenido = descargar(url)
            except OSError as error:
                self.stderr.write(self.style.WARNING(
                    f'  {ruta}: descarga fallida ({error})'))
                continue
            if default_storage.exists(ruta):
                default_storage.delete(ruta)
            default_storage.save(ruta, ContentFile(contenido))
            rutas.append(ruta)
        return rutas

    def _urls_para(self, sustantivo: str, termino: str, claves: tuple,
                   cantidad: int) -> list:
        """Primero las categorias curadas; la busqueda de texto solo si
        ninguna de ellas alcanza a dar las fotos pedidas."""
        for categoria in CATEGORIAS_COMMONS.get(sustantivo, ()):
            try:
                urls = fotos_de_categoria(categoria, cantidad)
            except OSError as error:
                self.stderr.write(self.style.WARNING(
                    f'  Category:{categoria} fallo ({error})'))
                continue
            if len(urls) == cantidad:
                return urls
        try:
            return buscar_fotos(termino, claves, cantidad)
        except OSError as error:
            self.stderr.write(self.style.WARNING(
                f'  {sustantivo}: busqueda fallida ({error})'))
            return []

    def _asignar(self, rutas_por_sustantivo: dict) -> None:
        """Reparte las fotos entre los productos cuyo nombre empieza por el
        sustantivo correspondiente, rotando para que dos productos vecinos
        del mismo tipo no salgan con la misma foto."""
        actualizados = 0
        sin_foto = 0
        pendientes = []
        contadores: dict[str, int] = {}

        for producto in Producto.objects.only('id', 'nombre', 'imagen').iterator():
            sustantivo = next(
                (s for s in SUSTANTIVOS if producto.nombre.startswith(s)), None)
            rutas = rutas_por_sustantivo.get(sustantivo) if sustantivo else None
            if not rutas:
                sin_foto += 1
                continue
            turno = contadores.get(sustantivo, 0)
            contadores[sustantivo] = turno + 1
            producto.imagen.name = rutas[turno % len(rutas)]
            pendientes.append(producto)
            actualizados += 1
            if len(pendientes) >= 200:
                self._guardar(pendientes)
                pendientes = []
        if pendientes:
            self._guardar(pendientes)

        self.stdout.write(self.style.SUCCESS(
            f'{actualizados} productos con foto real.'))
        if sin_foto:
            self.stdout.write(
                f'{sin_foto} productos sin foto (nombre fuera del catalogo demo).')

    @staticmethod
    def _guardar(productos: list) -> None:
        with transaction.atomic():
            Producto.objects.bulk_update(productos, ['imagen'])
