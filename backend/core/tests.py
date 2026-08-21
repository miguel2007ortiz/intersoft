from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (Categoria, Cliente, DetalleVenta, Empresa, MovimientoInventario,
                     Notificacion, Producto, Venta)


class BaseCoreTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Tienda Test", nit="900999998")
        cls.cuenta = User.objects.create_user(username="vendedor@test.co",
                                              email="vendedor@test.co",
                                              password="Clave12345")
        cls.cliente = Cliente.objects.create(empresa=cls.empresa, nombre="Carlos Ramirez",
                                             tipo_documento="CC", numero_documento="1020304050")
        cls.producto = Producto.objects.create(empresa=cls.empresa, nombre="Zapatos",
                                               sku="SKU-T01", precio=75000, stock=40,
                                               stock_minimo=10)

    @classmethod
    def crear_venta(cls, total=75000):
        return Venta.objects.create(empresa=cls.empresa, cliente=cls.cliente,
                                    vendedor=cls.cuenta, total=total, estado="completada")


class ValidacionesGlobalesTest(BaseCoreTest):
    def test_precio_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(empresa=self.empresa, nombre="Malo", sku="SKU-X1",
                                        precio=-1)

    def test_stock_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(empresa=self.empresa, nombre="Malo", sku="SKU-X2",
                                        stock=-5)

    def test_stock_minimo_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(empresa=self.empresa, nombre="Malo", sku="SKU-X3",
                                        stock_minimo=-1)

    def test_total_venta_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_venta(total=-100)

    def test_cero_es_valido(self):
        producto = Producto.objects.create(empresa=self.empresa, nombre="Gratis", sku="SKU-X4",
                                           precio=0, stock=0)
        self.assertEqual(producto.precio, 0)
        self.assertTrue(producto.stock_bajo)   # 0 <= 10 por defecto


class ClienteDocumentoUnicoTest(BaseCoreTest):
    def test_documento_repetido_en_la_misma_empresa_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cliente.objects.create(empresa=self.empresa, nombre="Duplicado",
                                       tipo_documento="CC", numero_documento="1020304050")

    def test_mismo_documento_en_otra_empresa_permitido(self):
        otra = Empresa.objects.create(nombre="Otra Tienda", nit="900999997")
        cliente = Cliente.objects.create(empresa=otra, nombre="Homonimo",
                                         tipo_documento="CC", numero_documento="1020304050")
        self.assertEqual(cliente.numero_documento, "1020304050")

    def test_cliente_puede_enlazar_cuenta_de_usuario(self):
        cliente = Cliente.objects.create(empresa=self.empresa, nombre="Con Cuenta",
                                         tipo_documento="CE", numero_documento="555555",
                                         usuario=self.cuenta)
        self.assertEqual(cliente.usuario.email, "vendedor@test.co")
        self.assertEqual(self.cuenta.perfil_cliente.nombre, "Con Cuenta")


class DetalleVentaTest(BaseCoreTest):
    def test_linea_y_subtotal(self):
        venta = self.crear_venta()
        detalle = DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                              cantidad=2, precio_unitario=75000)
        self.assertEqual(detalle.subtotal, 150000)
        self.assertEqual(venta.detalles.count(), 1)

    def test_mismo_producto_no_se_repite_en_la_venta(self):
        venta = self.crear_venta()
        DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                    cantidad=1, precio_unitario=75000)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                            cantidad=3, precio_unitario=75000)

    def test_cantidad_cero_rechazada(self):
        venta = self.crear_venta()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                            cantidad=0, precio_unitario=75000)

    def test_precio_unitario_negativo_rechazado(self):
        venta = self.crear_venta()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                            cantidad=1, precio_unitario=-10)


class MovimientoInventarioTest(BaseCoreTest):
    def test_registrar_entrada_salida_ajuste(self):
        for tipo in ("entrada", "salida", "ajuste"):
            movimiento = MovimientoInventario.objects.create(
                producto=self.producto, usuario=self.cuenta, tipo=tipo,
                cantidad=5, motivo=f"prueba {tipo}")
            self.assertEqual(movimiento.get_tipo_display(),
                             {"entrada": "Entrada", "salida": "Salida", "ajuste": "Ajuste"}[tipo])
        self.assertEqual(self.producto.movimientos.count(), 3)

    def test_cantidad_cero_rechazada(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovimientoInventario.objects.create(producto=self.producto, tipo="entrada",
                                                    cantidad=0, motivo="invalido")


class NotificacionTest(BaseCoreTest):
    def test_crear_y_marcar_leida(self):
        aviso = Notificacion.objects.create(usuario=self.cuenta,
                                            mensaje="Camiseta Polo tiene stock bajo")
        self.assertFalse(aviso.leida)
        aviso.leida = True
        aviso.save(update_fields=["leida"])
        aviso.refresh_from_db()
        self.assertTrue(aviso.leida)
        self.assertIn("stock bajo", str(aviso))


class BorradoLogicoTest(BaseCoreTest):
    def test_soft_delete_producto(self):
        self.producto.soft_delete()
        self.producto.refresh_from_db()
        self.assertIsNotNone(self.producto.deleted_at)
        self.assertFalse(self.producto.esta_activo)


class VentaFacturaTest(BaseCoreTest):
    def test_numero_factura_autogenerado(self):
        venta = self.crear_venta()
        self.assertTrue(venta.numero_factura)
        otra = self.crear_venta(total=100)
        self.assertNotEqual(venta.numero_factura, otra.numero_factura)
