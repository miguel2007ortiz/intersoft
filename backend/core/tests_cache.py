"""Fase B1: cache de negocio por version (core/cache_key.py) y su
invalidacion automatica via señales.

El cache puede ser LocMem (tests), por BD MySQL o Redis; la invalidacion
por "generacion" es O(1) y solo afecta al bucket de la empresa tocada, sin
borrar contexto IA ni contadores de rate-limit ni datos de otros tenants.
"""
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from cuentas.models import Perfil, Rol

from .cache_key import (generacion, invalidar, invalidar_catalogo,
                        invalidar_empresa)
from .models import (Categoria, Cliente, DetalleVenta, Empresa,
                     MovimientoInventario, Producto, Venta)


class CacheKeyTest(TestCase):
    def test_generacion_crece_al_invalidar(self):
        ns, alcance = 'analitica', 'empresa-x'
        antes = int(generacion(ns, alcance))
        invalidar(ns, alcance)
        self.assertEqual(int(generacion(ns, alcance)), antes + 1)

    def test_invalidar_empresa_es_aislado_por_bucket(self):
        g_an_1 = int(generacion('analitica', 'e1'))
        g_ia_1 = int(generacion('ia', 'e1'))
        g_an_2 = int(generacion('analitica', 'e2'))
        g_cat = int(generacion('cat', 'global'))

        invalidar_empresa('e1')

        self.assertEqual(int(generacion('analitica', 'e1')), g_an_1 + 1)
        self.assertEqual(int(generacion('ia', 'e1')), g_ia_1 + 1)
        # No toca otras empresas ni el catalogo.
        self.assertEqual(int(generacion('analitica', 'e2')), g_an_2)
        self.assertEqual(int(generacion('cat', 'global')), g_cat)

    def test_invalidar_catalogo_no_toca_analitica(self):
        g_an = int(generacion('analitica', 'e1'))
        g_cat = int(generacion('cat', 'global'))
        invalidar_catalogo()
        self.assertEqual(int(generacion('cat', 'global')), g_cat + 1)
        self.assertEqual(int(generacion('analitica', 'e1')), g_an)


class InvalidacionPorSenalesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_roles')

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Tienda Cache',
                                              nit='900500001')
        self.admin = User.objects.create_user(
            username='admincache@test.co', email='admincache@test.co',
            password='Clave12345')
        Perfil.objects.create(usuario=self.admin, empresa=self.empresa,
                              rol=Rol.de_nombre('ADMINISTRADOR'))
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, nombre='Cliente Cache', tipo_documento='CC',
            numero_documento='1002003001')

    def _gen_an(self):
        return int(generacion('analitica', str(self.empresa.id)))

    def test_venta_linea_y_movimiento_invalidan_la_empresa(self):
        categoria = Categoria.objects.create(empresa=self.empresa,
                                             nombre='Calzado')
        producto = Producto.objects.create(
            empresa=self.empresa, categoria=categoria, nombre='Zapato',
            sku='CACH-1', precio=10000, stock=5, stock_minimo=2)

        g0 = self._gen_an()
        venta = Venta.objects.create(empresa=self.empresa, cliente=self.cliente,
                                     vendedor=self.admin, metodo_pago='efectivo')
        self.assertEqual(self._gen_an(), g0 + 1)

        g0 = self._gen_an()
        DetalleVenta.objects.create(venta=venta, producto=producto,
                                    cantidad=1, precio_unitario=10000)
        self.assertEqual(self._gen_an(), g0 + 1)

        g0 = self._gen_an()
        MovimientoInventario.objects.create(producto=producto,
                                            usuario=self.admin, tipo='ajuste',
                                            cantidad=1, motivo='prueba')
        self.assertEqual(self._gen_an(), g0 + 1)

    def test_producto_y_categoria_invalidan_el_catalogo(self):
        def gen_cat():
            return int(generacion('cat', 'global'))

        g0 = gen_cat()
        categoria = Categoria.objects.create(empresa=self.empresa,
                                             nombre='Ropa')
        self.assertEqual(gen_cat(), g0 + 1)

        g0 = gen_cat()
        Producto.objects.create(empresa=self.empresa, categoria=categoria,
                                nombre='Camisa', sku='CACH-2', precio=12000,
                                stock=3, stock_minimo=1)
        self.assertEqual(gen_cat(), g0 + 1)


class CrearCacheCommandTest(TestCase):
    def test_es_idempotente(self):
        call_command('crear_cache')
        call_command('crear_cache')  # no debe lanzar ni romper la segunda vez