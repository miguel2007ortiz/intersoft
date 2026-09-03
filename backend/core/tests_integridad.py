"""Fase A1: integridad financiera de las ventas.

Verifica que los totales de una venta siempre reflejen la suma de sus
lineas de detalle, aun cuando se agregan, editan o eliminan lineas, y que
el descuento se conserve al recalcular (no se pierde el del cupon/POS).
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TransactionTestCase

from cuentas.models import Perfil, Rol

from .models import Cliente, DetalleVenta, Empresa, Producto, Venta
from .signals import recalcular_totales_venta


class IntegridadVentasTest(TransactionTestCase):
    """Venta con descuento y multiples productos del mismo objeto de negocio.

    Usa TransactionTestCase porque las senales persisten via ``.update()``
    y es necesario leer el resultado committado (REPEATABLE READ de MySQL
    devolveria un snapshot stale dentro de un TestCase transaccional).
    """

    @classmethod
    def _base(cls):
        call_command("seed_roles")

        cls.empresa = Empresa.objects.create(nombre="Tienda Integridad",
                                             nit="900400001")
        cls.admin = User.objects.create_user(
            username="adminint@test.co", email="adminint@test.co",
            password="Clave12345")
        Perfil.objects.create(usuario=cls.admin, empresa=cls.empresa,
                              rol=Rol.de_nombre('ADMINISTRADOR'))

        cls.cliente = Cliente.objects.create(
            empresa=cls.empresa, nombre="Cliente Int",
            tipo_documento="CC", numero_documento="3033333333")

        cls.p1 = Producto.objects.create(empresa=cls.empresa, nombre="Camisa",
                                         sku="SKU-I1", precio=35000, stock=20)
        cls.p2 = Producto.objects.create(empresa=cls.empresa, nombre="Pantalon",
                                         sku="SKU-I2", precio=42000, stock=15)

    def setUp(self):
        self._base()

    def _venta(self, descuento=0):
        return Venta.objects.create(empresa=self.empresa, cliente=self.cliente,
                                    vendedor=self.admin, descuento=descuento,
                                    estado="completada")

    def test_crear_detalle_actualiza_subtotal_y_total(self):
        venta = self._venta(descuento=0)
        DetalleVenta.objects.create(venta=venta, producto=self.p1,
                                    cantidad=2, precio_unitario=35000)

        venta.refresh_from_db()
        self.assertEqual(venta.subtotal, Decimal("70000"))
        self.assertEqual(venta.total, Decimal("70000"))

    def test_eliminar_detalle_actualiza_totales(self):
        venta = self._venta(descuento=Decimal("10000"))
        DetalleVenta.objects.create(venta=venta, producto=self.p1,
                                    cantidad=2, precio_unitario=35000)
        DetalleVenta.objects.create(venta=venta, producto=self.p2,
                                    cantidad=1, precio_unitario=42000)
        venta.refresh_from_db()
        self.assertEqual(venta.subtotal, Decimal("112000"))
        self.assertEqual(venta.total, Decimal("102000"))

        # Quitar el segundo producto: el descuento se mantiene.
        venta.detalles.filter(producto=self.p2).delete()
        venta.refresh_from_db()
        self.assertEqual(venta.subtotal, Decimal("70000"))
        self.assertEqual(venta.total, Decimal("60000"))

    def test_sin_detalles_los_totales_quedan_en_cero(self):
        venta = self._venta(descuento=0)
        detalle = DetalleVenta.objects.create(venta=venta, producto=self.p1,
                                              cantidad=1, precio_unitario=35000)
        # La app borra detalles instancia por instancia (no con queryset
        # batch, que no dispara senales post_delete en Django).
        detalle.delete()
        venta.refresh_from_db()
        self.assertEqual(venta.subtotal, Decimal("0"))
        self.assertEqual(venta.total, Decimal("0"))

    def test_descuento_mayor_al_subtotal_total_queda_en_cero(self):
        venta = self._venta(descuento=Decimal("90000"))
        DetalleVenta.objects.create(venta=venta, producto=self.p1,
                                    cantidad=1, precio_unitario=35000)
        venta.refresh_from_db()
        self.assertEqual(venta.subtotal, Decimal("35000"))
        self.assertEqual(venta.total, Decimal("0"))

    def test_recalcular_invocado_manualmente_no_refresca_descuento(self):
        venta = self._venta(descuento=Decimal("5000"))
        DetalleVenta.objects.create(venta=venta, producto=self.p1,
                                    cantidad=2, precio_unitario=35000)
        venta.refresh_from_db()
        recalcular_totales_venta(venta)
        venta.refresh_from_db()
        self.assertEqual(venta.subtotal, Decimal("70000"))
        self.assertEqual(venta.total, Decimal("65000"))
        self.assertEqual(venta.descuento, Decimal("5000"))