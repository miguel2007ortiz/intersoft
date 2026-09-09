"""Tests del adaptador de pasarela de pago (Fase 3).

Tests aislados del adaptador mock + integracion de idempotencia en checkout.
"""
import os
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cuentas.models import Perfil, Rol

from .models import Cliente, Empresa, IntentoPago, Producto, Venta
from .services.pasarela_adapter import (
    RespuestaPago,
    cobrar,
)


class PasarelaMockTest(TestCase):
    """Tests unitarios del adaptador mock."""

    def test_cobrar_aprobado_determinista(self):
        r1 = cobrar(monto=1000, idempotencia_clave="clave123")
        r2 = cobrar(monto=1000, idempotencia_clave="clave123")
        self.assertTrue(r1.aprobada)
        self.assertTrue(r2.aprobada)
        self.assertEqual(r1.transaccion_id, r2.transaccion_id)

    def test_cobrar_diferente_clave_diferente_id(self):
        r1 = cobrar(monto=1000, idempotencia_clave="claveA")
        r2 = cobrar(monto=1000, idempotencia_clave="claveB")
        self.assertNotEqual(r1.transaccion_id, r2.transaccion_id)

    def test_forzar_rechazo(self):
        r = cobrar(monto=1000, idempotencia_clave="k", forzar_rechazo=True)
        self.assertFalse(r.aprobada)
        self.assertEqual(r.estado, 'rechazado')

    def test_respuesta_datos_completos(self):
        r = cobrar(monto=50000, moneda='COP', metodo_pago='tarjeta',
                   referencia='ref1', idempotencia_clave='k1')
        self.assertTrue(r.aprobada)
        self.assertEqual(r.mensaje, 'Pago aprobado (mock).')
        self.assertIn('monto', r.crudo)
        self.assertEqual(r.crudo['monto'], '50000')
        self.assertIn('resuelto', r.crudo)

    def test_forzar_rechazo_transaccion_id_presente(self):
        r = cobrar(monto=1000, idempotencia_clave="k", forzar_rechazo=True)
        self.assertTrue(r.transaccion_id.startswith('MOCK-'))

    @override_settings()
    def test_pasarla_real_no_configurada(self):
        os.environ['PASARELA_MOCK'] = 'false'
        try:
            r = cobrar(monto=1000, idempotencia_clave="k")
            self.assertFalse(r.aprobada)
            self.assertEqual(r.estado, 'rechazado')
            self.assertIn('SIN_CONFIGURACION', r.crudo.get('error', ''))
        finally:
            os.environ.pop('PASARELA_MOCK', None)
            os.environ['PASARELA_MOCK'] = 'true'


class RespuestaPagoDataclassTest(TestCase):
    def test_defaults(self):
        r = RespuestaPago(aprobada=False)
        self.assertFalse(r.aprobada)
        self.assertEqual(r.transaccion_id, '')
        self.assertEqual(r.estado, 'pendiente')
        self.assertEqual(r.mensaje, '')
        self.assertEqual(r.crudo, {})


class MarketplaceCheckoutIdempotenciaTest(TestCase):
    """Fase 3: idempotencia del checkout (doble POST misma clave)."""

    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Empresa.objects.create(nombre="Vend", nit="900777001")
        cls.producto = Producto.objects.create(
            empresa=cls.vendedor, nombre="Widget", sku="IDEM-1",
            precio=25000, stock=20, activo=True)
        cls.comprador = User.objects.create_user(
            username="idem@test.co", email="idem@test.co",
            password="Clave12345")
        Perfil.objects.create(usuario=cls.comprador, empresa=None,
                              rol=Rol.de_nombre("CLIENTE"))
        cls.cliente = Cliente.objects.create(
            usuario=cls.comprador, empresa=None, nombre="Idem Buyer",
            tipo_documento="CC", numero_documento="88888888",
            email="idem@test.co", direccion="Calle 10 # 5-20", ciudad="Bogota")

    def _api(self):
        api = APIClient()
        api.force_authenticate(self.comprador)
        return api

    def test_doble_post_misma_clave_un_solo_cobro(self):
        api = self._api()
        api.post("/api/tienda/carrito/items/",
                 {"producto": str(self.producto.id), "cantidad": 2},
                 format="json")
        r1 = api.post("/api/tienda/checkout/",
                      {"metodo_pago": "tarjeta"}, format="json")
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(IntentoPago.objects.filter(estado='aprobado').count(), 1)

        # Carrito ya vacio -> segundo post es CARRITO_VACIO (carrito limpio)
        r2 = api.post("/api/tienda/checkout/",
                      {"metodo_pago": "tarjeta"}, format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(IntentoPago.objects.filter(estado='aprobado').count(), 1)

    def test_transaccion_id_consistente(self):
        api = self._api()
        api.post("/api/tienda/carrito/items/",
                 {"producto": str(self.producto.id), "cantidad": 1},
                 format="json")
        api.post("/api/tienda/checkout/",
                 {"metodo_pago": "tarjeta"}, format="json")
        intento = IntentoPago.objects.first()
        venta = Venta.objects.first()
        self.assertEqual(intento.transaccion_id, venta.transaccion_id)

    def test_rechazo_luego_exito_genera_dos_intentos(self):
        api = self._api()
        api.post("/api/tienda/carrito/items/",
                 {"producto": str(self.producto.id), "cantidad": 1},
                 format="json")
        rechazo = RespuestaPago(
            aprobada=False, transaccion_id='MOCK-RECHAZADO',
            estado='rechazado', mensaje='Pago rechazado (mock forzado).',
            crudo={'resuelto': 'RECHAZADO'}, pasarela='mock')
        with patch('core.views_tienda.cobrar', return_value=rechazo):
            r1 = api.post("/api/tienda/checkout/",
                          {"metodo_pago": "tarjeta"}, format="json")
        self.assertEqual(r1.status_code, 402)
        self.assertEqual(IntentoPago.objects.count(), 1)
        self.assertEqual(IntentoPago.objects.first().estado, 'rechazado')

        r2 = api.post("/api/tienda/checkout/",
                      {"metodo_pago": "tarjeta"}, format="json")
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(IntentoPago.objects.count(), 1)
        self.assertEqual(IntentoPago.objects.first().estado, 'aprobado')
        self.assertEqual(Venta.objects.filter(estado_pago='aprobado').count(), 1)
