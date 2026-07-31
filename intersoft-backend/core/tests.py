"""
Pruebas básicas de InterSoft.

Ejecutar con:  python manage.py test core
"""

from django.test import TestCase
from .models import Empresa, Cliente, Producto, Categoria, Venta


class EmpresaTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Test SAS', nit='111', email='t@test.co'
        )

    def test_str(self):
        self.assertIn('Test SAS', str(self.empresa))

    def test_plan_por_defecto(self):
        self.assertEqual(self.empresa.plan, 'basic')


class ProductoTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='E', nit='222', email='e@e.co')
        self.cat = Categoria.objects.create(empresa=self.empresa, nombre='Cat')

    def test_stock_bajo_true(self):
        p = Producto.objects.create(
            empresa=self.empresa, categoria=self.cat, nombre='P',
            sku='S1', precio=100, stock=5, stock_minimo=10
        )
        self.assertTrue(p.stock_bajo)

    def test_stock_bajo_false(self):
        p = Producto.objects.create(
            empresa=self.empresa, categoria=self.cat, nombre='P2',
            sku='S2', precio=100, stock=50, stock_minimo=10
        )
        self.assertFalse(p.stock_bajo)


class VentaTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='E', nit='333', email='v@v.co')
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, nombre='C', numero_documento='1'
        )

    def test_numero_factura_automatico(self):
        venta = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, total=1000
        )
        self.assertTrue(venta.numero_factura)
        self.assertIn('-', venta.numero_factura)

    def test_soft_delete(self):
        venta = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, total=1000
        )
        venta.soft_delete()
        self.assertIsNotNone(venta.deleted_at)
        self.assertFalse(venta.esta_activo)
