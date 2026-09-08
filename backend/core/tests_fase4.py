"""Tests de la Fase 4: pasarela real (Wompi sandbox) y webhook firmado.

Cubre las tres piezas del cobro asincrono:

- El adaptador en modo real: firma de integridad del Web Checkout y respuesta
  'pendiente' (nunca 'aprobado' sin confirmacion de la pasarela).
- El webhook: validacion de firma, verificacion autoritativa contra la API,
  cuadre de monto e idempotencia frente a reintentos.
- El endpoint de estado que consulta el frontend al volver del checkout.

Todos los escenarios usan credenciales de mentira y no salen a la red: la
unica llamada saliente posible (``verificar_transaccion_wompi``) se parchea o
se deja sin credenciales a proposito.
"""
import hashlib
import json
import os
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from cuentas.models import Perfil, Rol

from .models import Cliente, Empresa, IntentoPago, Producto, Venta
from .services.pasarela_adapter import (
    RespuestaPago,
    a_centavos,
    cobrar,
    firma_integridad_wompi,
    respuesta_desde_transaccion_wompi,
    validar_firma_webhook_wompi,
)

SECRETO_EVENTOS = 'stagtest_events_ABC123'
SECRETO_INTEGRIDAD = 'stagtest_integrity_XYZ789'

# Entorno "Wompi configurado". Se declaran las cuatro variables siempre (aunque
# sea en vacio) para que el resultado no dependa del .env de quien corra los
# tests.
ENTORNO_WOMPI = {
    'PASARELA_MOCK': 'False',
    'WOMPI_SANDBOX': 'True',
    'WOMPI_PUBLIC_KEY': 'pub_test_llave',
    'WOMPI_PRIVATE_KEY': 'prv_test_llave',
    'WOMPI_INTEGRITY_SECRET': SECRETO_INTEGRIDAD,
    'WOMPI_EVENTS_SECRET': SECRETO_EVENTOS,
    'WOMPI_REDIRECT_URL': 'http://localhost:4200/pago/retorno',
}


def entorno(**cambios):
    """Entorno Wompi con los ajustes indicados (patch.dict de os.environ)."""
    valores = {**ENTORNO_WOMPI, **cambios}
    return patch.dict(os.environ, valores)


def construir_evento(referencia, estado, monto_centavos,
                     transaccion_id='wompi-tx-1', secreto=SECRETO_EVENTOS,
                     evento='transaction.updated', timestamp=1725000000):
    """Arma un evento de Wompi con su checksum correctamente calculado.

    Reproduce el algoritmo publicado (concatenar los valores de
    ``signature.properties`` leidos desde ``data``, luego el timestamp, luego
    el secreto) para poder firmar eventos de prueba como lo haria Wompi.
    """
    cuerpo = {
        'event': evento,
        'data': {
            'transaction': {
                'id': transaccion_id,
                'status': estado,
                'reference': referencia,
                'amount_in_cents': monto_centavos,
                'currency': 'COP',
            }
        },
        'timestamp': timestamp,
        'signature': {
            'properties': [
                'transaction.id',
                'transaction.status',
                'transaction.amount_in_cents',
            ],
        },
    }
    cadena = (f"{transaccion_id}{estado}{monto_centavos}"
              f"{timestamp}{secreto}")
    cuerpo['signature']['checksum'] = hashlib.sha256(
        cadena.encode('utf-8')).hexdigest()
    return cuerpo


# --------------------------- Adaptador (unitarios) -------------------------

class FirmaIntegridadTest(TestCase):
    """La firma del enlace del Web Checkout."""

    def test_orden_de_concatenacion(self):
        # El valor esperado se construye aqui a mano, no llamando a la funcion:
        # lo que se esta fijando es el ORDEN (referencia, monto, moneda,
        # secreto), que es justo lo que se rompe al integrar.
        esperado = hashlib.sha256(
            b'ref-1' + b'100000' + b'COP' + SECRETO_INTEGRIDAD.encode()
        ).hexdigest()
        self.assertEqual(
            firma_integridad_wompi('ref-1', 100000, 'COP', SECRETO_INTEGRIDAD),
            esperado)

    def test_monto_distinto_firma_distinta(self):
        a = firma_integridad_wompi('ref-1', 100000, 'COP', SECRETO_INTEGRIDAD)
        b = firma_integridad_wompi('ref-1', 100001, 'COP', SECRETO_INTEGRIDAD)
        self.assertNotEqual(a, b)

    def test_moneda_se_normaliza_a_mayusculas(self):
        self.assertEqual(
            firma_integridad_wompi('r', 1, 'cop', SECRETO_INTEGRIDAD),
            firma_integridad_wompi('r', 1, 'COP', SECRETO_INTEGRIDAD))


class CentavosTest(TestCase):
    """Conversion a centavos: el redondeo binario aqui firma un monto erroneo."""

    def test_decimal_con_centavos(self):
        self.assertEqual(a_centavos('1000.10'), 100010)

    def test_entero(self):
        self.assertEqual(a_centavos(25000), 2500000)

    def test_no_usa_float(self):
        # float('1000.1') * 100 == 100009.99999999999 -> int() daria 100009.
        self.assertEqual(a_centavos('1000.1'), 100010)


class CobrarModoRealTest(TestCase):
    """``cobrar`` con PASARELA_MOCK=False (no sale a la red)."""

    def test_sin_credenciales(self):
        with entorno(WOMPI_PUBLIC_KEY='', WOMPI_PRIVATE_KEY=''):
            r = cobrar(monto=50000, idempotencia_clave='ref-1')
        self.assertFalse(r.aprobada)
        self.assertEqual(r.estado, 'rechazado')
        self.assertEqual(r.crudo.get('error'), 'SIN_CONFIGURACION')

    def test_sin_secreto_de_integridad(self):
        with entorno(WOMPI_INTEGRITY_SECRET=''):
            r = cobrar(monto=50000, idempotencia_clave='ref-1')
        self.assertFalse(r.aprobada)
        self.assertEqual(r.crudo.get('error'), 'SIN_SECRETO_INTEGRIDAD')

    def test_devuelve_pendiente_no_aprobado(self):
        # Lo esencial de la Fase 4: en modo real nadie queda pagado sin que la
        # pasarela lo confirme por webhook.
        with entorno():
            r = cobrar(monto=50000, idempotencia_clave='ref-1')
        self.assertEqual(r.estado, 'pendiente')
        self.assertFalse(r.aprobada)
        self.assertEqual(r.pasarela, 'wompi')

    def test_datos_checkout_completos_y_firmados(self):
        with entorno():
            r = cobrar(monto=50000, moneda='COP', idempotencia_clave='ref-1')
        datos = r.datos_checkout
        self.assertEqual(datos['reference'], 'ref-1')
        self.assertEqual(datos['amount_in_cents'], 5000000)
        self.assertEqual(datos['currency'], 'COP')
        self.assertEqual(datos['public_key'], 'pub_test_llave')
        self.assertEqual(
            datos['signature_integrity'],
            firma_integridad_wompi('ref-1', 5000000, 'COP', SECRETO_INTEGRIDAD))
        self.assertEqual(datos['redirect_url'],
                         'http://localhost:4200/pago/retorno')

    def test_datos_checkout_no_filtran_secretos(self):
        # Estos datos viajan al navegador del comprador: si la llave privada o
        # alguno de los secretos apareciera aqui, quedaria publicado.
        with entorno():
            r = cobrar(monto=50000, idempotencia_clave='ref-1')
        serializado = json.dumps(r.datos_checkout)
        self.assertNotIn('prv_test_llave', serializado)
        self.assertNotIn(SECRETO_INTEGRIDAD, serializado)
        self.assertNotIn(SECRETO_EVENTOS, serializado)

    def test_modo_mock_sigue_aprobando(self):
        # La Fase 4 no debe cambiar el comportamiento por defecto.
        with patch.dict(os.environ, {'PASARELA_MOCK': 'True'}):
            r = cobrar(monto=50000, idempotencia_clave='ref-1')
        self.assertTrue(r.aprobada)
        self.assertEqual(r.pasarela, 'mock')


class EstadoTransaccionWompiTest(TestCase):
    """Traduccion del vocabulario de Wompi al estado normalizado."""

    def test_aprobada(self):
        r = respuesta_desde_transaccion_wompi({'id': 't1', 'status': 'APPROVED'})
        self.assertTrue(r.aprobada)
        self.assertEqual(r.estado, 'aprobado')
        self.assertEqual(r.transaccion_id, 't1')

    def test_rechazos(self):
        for estado in ('DECLINED', 'VOIDED', 'ERROR'):
            with self.subTest(estado=estado):
                r = respuesta_desde_transaccion_wompi({'status': estado})
                self.assertFalse(r.aprobada)
                self.assertEqual(r.estado, 'rechazado')

    def test_pendiente(self):
        r = respuesta_desde_transaccion_wompi({'status': 'PENDING'})
        self.assertEqual(r.estado, 'pendiente')

    def test_estado_desconocido_no_aprueba(self):
        # Ante un estado nuevo que Wompi agregue, lo seguro es no dar por
        # pagada la venta.
        r = respuesta_desde_transaccion_wompi({'status': 'INVENTADO'})
        self.assertFalse(r.aprobada)
        self.assertEqual(r.estado, 'pendiente')


class FirmaWebhookTest(TestCase):
    """Validacion de la firma de eventos (control de acceso del webhook)."""

    def _evento(self):
        return construir_evento('ref-1', 'APPROVED', 5000000)

    def test_firma_valida(self):
        e = self._evento()
        self.assertTrue(validar_firma_webhook_wompi(
            e, SECRETO_EVENTOS, e['signature']['checksum']))

    def test_secreto_incorrecto(self):
        e = self._evento()
        self.assertFalse(validar_firma_webhook_wompi(
            e, 'otro_secreto', e['signature']['checksum']))

    def test_monto_alterado(self):
        e = self._evento()
        checksum = e['signature']['checksum']
        e['data']['transaction']['amount_in_cents'] = 1
        self.assertFalse(validar_firma_webhook_wompi(
            e, SECRETO_EVENTOS, checksum))

    def test_estado_alterado(self):
        e = construir_evento('ref-1', 'DECLINED', 5000000)
        checksum = e['signature']['checksum']
        e['data']['transaction']['status'] = 'APPROVED'
        self.assertFalse(validar_firma_webhook_wompi(
            e, SECRETO_EVENTOS, checksum))

    def test_sin_propiedades_no_valida(self):
        # Un evento sin 'properties' firmaria solo timestamp+secreto: aceptarlo
        # dejaria pasar cualquier transaccion con un checksum reutilizado.
        e = self._evento()
        e['signature']['properties'] = []
        self.assertFalse(validar_firma_webhook_wompi(
            e, SECRETO_EVENTOS, e['signature']['checksum']))

    def test_sin_secreto_no_valida(self):
        e = self._evento()
        self.assertFalse(validar_firma_webhook_wompi(
            e, '', e['signature']['checksum']))

    def test_sin_checksum_no_valida(self):
        self.assertFalse(validar_firma_webhook_wompi(
            self._evento(), SECRETO_EVENTOS, ''))


# ----------------------- Base comun de los tests de API --------------------

class BasePagoAsincronoTest(TestCase):
    """Comprador con carrito listo para un checkout en modo Wompi."""

    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Empresa.objects.create(nombre="Vend F4", nit="900777004")
        cls.producto = Producto.objects.create(
            empresa=cls.vendedor, nombre="Widget F4", sku="F4-1",
            precio=25000, stock=20, activo=True)
        cls.comprador = User.objects.create_user(
            username="f4@test.co", email="f4@test.co", password="Clave12345")
        Perfil.objects.create(usuario=cls.comprador, empresa=None,
                              rol=Rol.de_nombre("CLIENTE"))
        cls.cliente = Cliente.objects.create(
            usuario=cls.comprador, empresa=None, nombre="F4 Buyer",
            tipo_documento="CC", numero_documento="44444444",
            email="f4@test.co")

    def api(self, usuario=None):
        cliente_api = APIClient()
        cliente_api.force_authenticate(usuario or self.comprador)
        return cliente_api

    def iniciar_checkout(self, cantidad=2):
        """Deja un checkout en estado pendiente y devuelve (respuesta, intento).

        Se parchea ``verificar_transaccion_wompi`` fuera de este metodo; aqui
        el adaptador no sale a la red porque el modo real solo firma el enlace.
        """
        api = self.api()
        api.post("/api/tienda/carrito/items/",
                 {"producto": str(self.producto.id), "cantidad": cantidad},
                 format="json")
        with entorno():
            respuesta = api.post("/api/tienda/checkout/",
                                 {"metodo_pago": "tarjeta"}, format="json")
        return respuesta, IntentoPago.objects.filter(
            usuario=self.comprador).first()

    def enviar_webhook(self, evento, verificada=False):
        """POST al webhook sin autenticacion (como lo haria Wompi).

        Por defecto ``verificar_transaccion_wompi`` devuelve None (sin
        credenciales de API), de modo que se ejerce la ruta de respaldo: el
        cuerpo ya validado por firma.
        """
        anonimo = APIClient()
        with entorno():
            with patch('core.views_tienda.verificar_transaccion_wompi',
                       return_value=verificada or None):
                return anonimo.post("/api/tienda/pagos/webhook/wompi/",
                                    evento, format="json")


# ------------------------- Checkout en modo asincrono ----------------------

class CheckoutPendienteTest(BasePagoAsincronoTest):
    """El checkout con pasarela real responde 202 y espera al webhook."""

    def test_responde_202_con_datos_de_checkout(self):
        respuesta, intento = self.iniciar_checkout()
        self.assertEqual(respuesta.status_code, 202)
        self.assertEqual(respuesta.data['codigo'], 'PAGO_PENDIENTE')
        self.assertEqual(respuesta.data['datos_checkout']['reference'],
                         intento.idempotencia_clave)

    def test_stock_queda_reservado(self):
        self.iniciar_checkout(cantidad=2)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 18)

    def test_carrito_no_se_vacia(self):
        self.iniciar_checkout()
        api = self.api()
        carrito = api.get("/api/tienda/carrito/").data
        self.assertEqual(len(carrito['items']), 1)

    def test_venta_no_queda_pagada(self):
        # Sin confirmacion de la pasarela, ninguna venta puede figurar como
        # aprobada: es la garantia de no entregar mercancia sin cobrar.
        self.iniciar_checkout()
        self.assertEqual(
            Venta.objects.filter(estado_pago='aprobado').count(), 0)
        self.assertEqual(
            Venta.objects.filter(estado_pago='pendiente').count(), 1)

    def test_intento_queda_pendiente(self):
        _, intento = self.iniciar_checkout()
        self.assertEqual(intento.estado, 'pendiente')

    def test_segundo_checkout_no_reserva_de_nuevo(self):
        self.iniciar_checkout()
        api = self.api()
        with entorno():
            segunda = api.post("/api/tienda/checkout/",
                               {"metodo_pago": "tarjeta"}, format="json")
        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(segunda.data['codigo'], 'PAGO_EN_CURSO')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 18)  # no se reservo dos veces
        self.assertEqual(Venta.objects.count(), 1)


# ------------------------------- Webhook -----------------------------------

class WebhookFirmaTest(BasePagoAsincronoTest):
    """Controles de acceso del endpoint publico."""

    def test_sin_secreto_configurado_responde_503(self):
        _, intento = self.iniciar_checkout()
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED',
                                  a_centavos(intento.monto_total))
        anonimo = APIClient()
        with entorno(WOMPI_EVENTS_SECRET=''):
            respuesta = anonimo.post("/api/tienda/pagos/webhook/wompi/",
                                     evento, format="json")
        self.assertEqual(respuesta.status_code, 503)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'pendiente')

    def test_firma_invalida_no_confirma(self):
        _, intento = self.iniciar_checkout()
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED',
                                  a_centavos(intento.monto_total),
                                  secreto='secreto_del_atacante')
        respuesta = self.enviar_webhook(evento)
        self.assertEqual(respuesta.status_code, 401)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'pendiente')
        self.assertEqual(
            Venta.objects.filter(estado_pago='aprobado').count(), 0)

    def test_cuerpo_manipulado_tras_firmar_no_confirma(self):
        # Escenario real de ataque: se copia un evento legitimo DECLINED y se
        # cambia el estado a APPROVED conservando el checksum original.
        _, intento = self.iniciar_checkout()
        evento = construir_evento(intento.idempotencia_clave, 'DECLINED',
                                  a_centavos(intento.monto_total))
        evento['data']['transaction']['status'] = 'APPROVED'
        respuesta = self.enviar_webhook(evento)
        self.assertEqual(respuesta.status_code, 401)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'pendiente')

    def test_no_requiere_autenticacion(self):
        # Wompi no lleva JWT: si el endpoint exigiera sesion, nunca llegaria
        # una notificacion y todas las ventas quedarian colgadas.
        _, intento = self.iniciar_checkout()
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED',
                                  a_centavos(intento.monto_total))
        respuesta = self.enviar_webhook(evento)
        self.assertEqual(respuesta.status_code, 200)

    def test_evento_de_otro_tipo_se_ignora(self):
        _, intento = self.iniciar_checkout()
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED',
                                  a_centavos(intento.monto_total),
                                  evento='nequi_token.updated')
        respuesta = self.enviar_webhook(evento)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['codigo'], 'EVENTO_IGNORADO')
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'pendiente')

    def test_referencia_desconocida(self):
        evento = construir_evento('referencia-que-no-existe', 'APPROVED', 100)
        respuesta = self.enviar_webhook(evento)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['codigo'], 'REFERENCIA_DESCONOCIDA')


class WebhookResolucionTest(BasePagoAsincronoTest):
    """Efecto del webhook sobre ventas, stock y carrito."""

    def test_aprobado_confirma_la_venta(self):
        _, intento = self.iniciar_checkout()
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED',
                                  a_centavos(intento.monto_total))
        respuesta = self.enviar_webhook(evento)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['codigo'], 'PAGO_CONFIRMADO')
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'aprobado')
        self.assertEqual(intento.transaccion_id, 'wompi-tx-1')

        venta = Venta.objects.get(intento_pago=intento)
        self.assertEqual(venta.estado, 'completada')
        self.assertEqual(venta.estado_pago, 'aprobado')
        self.assertEqual(venta.pasarela, 'wompi')
        self.assertEqual(venta.transaccion_id, 'wompi-tx-1')
        self.assertIsNotNone(venta.pagado_en)

    def test_aprobado_vacia_el_carrito(self):
        self.iniciar_checkout()
        intento = IntentoPago.objects.get(usuario=self.comprador)
        self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'APPROVED',
            a_centavos(intento.monto_total)))
        carrito = self.api().get("/api/tienda/carrito/").data
        self.assertEqual(len(carrito['items']), 0)

    def test_aprobado_no_devuelve_stock(self):
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'APPROVED',
            a_centavos(intento.monto_total)))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 18)

    def test_rechazado_devuelve_el_stock(self):
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        respuesta = self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'DECLINED',
            a_centavos(intento.monto_total)))

        self.assertEqual(respuesta.data['codigo'], 'PAGO_REVERSADO')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 20)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'rechazado')
        venta = Venta.objects.get(intento_pago=intento)
        self.assertEqual(venta.estado_pago, 'reversado')

    def test_rechazado_conserva_el_carrito(self):
        self.iniciar_checkout()
        intento = IntentoPago.objects.get(usuario=self.comprador)
        self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'DECLINED',
            a_centavos(intento.monto_total)))
        carrito = self.api().get("/api/tienda/carrito/").data
        self.assertEqual(len(carrito['items']), 1)

    def test_pendiente_no_resuelve_nada(self):
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        respuesta = self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'PENDING',
            a_centavos(intento.monto_total)))

        self.assertEqual(respuesta.data['codigo'], 'PAGO_PENDIENTE')
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'pendiente')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 18)


class WebhookIdempotenciaTest(BasePagoAsincronoTest):
    """Wompi reenvia el mismo evento hasta recibir un 2xx."""

    def test_reintento_de_aprobacion_no_duplica(self):
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED',
                                  a_centavos(intento.monto_total))

        primera = self.enviar_webhook(evento)
        segunda = self.enviar_webhook(evento)
        tercera = self.enviar_webhook(evento)

        self.assertEqual(primera.data['codigo'], 'PAGO_CONFIRMADO')
        self.assertEqual(segunda.data['codigo'], 'YA_PROCESADO')
        self.assertEqual(tercera.data['codigo'], 'YA_PROCESADO')
        self.assertEqual(segunda.status_code, 200)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 18)
        self.assertEqual(Venta.objects.count(), 1)

    def test_reintento_de_rechazo_no_devuelve_stock_dos_veces(self):
        # El fallo silencioso mas caro de un webhook mal hecho: cada reintento
        # sumaria unidades al inventario que nunca existieron.
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        evento = construir_evento(intento.idempotencia_clave, 'DECLINED',
                                  a_centavos(intento.monto_total))

        self.enviar_webhook(evento)
        self.enviar_webhook(evento)
        self.enviar_webhook(evento)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 20)

    def test_rechazo_despues_de_aprobacion_no_revierte(self):
        # Un evento tardio o reordenado no puede deshacer una venta ya cobrada.
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        monto = a_centavos(intento.monto_total)
        self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'APPROVED', monto))
        respuesta = self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'DECLINED', monto))

        self.assertEqual(respuesta.data['codigo'], 'YA_PROCESADO')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 18)
        venta = Venta.objects.get(intento_pago=intento)
        self.assertEqual(venta.estado_pago, 'aprobado')


class WebhookMontoTest(BasePagoAsincronoTest):
    """Cuadre entre lo reservado y lo notificado."""

    def test_monto_menor_no_confirma(self):
        _, intento = self.iniciar_checkout(cantidad=2)
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED', 100)
        respuesta = self.enviar_webhook(evento)

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data['codigo'], 'MONTO_NO_COINCIDE')
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'pendiente')
        self.assertEqual(
            Venta.objects.filter(estado_pago='aprobado').count(), 0)

    def test_monto_exacto_confirma(self):
        _, intento = self.iniciar_checkout(cantidad=2)
        # 2 x 25000 = 50000 COP = 5.000.000 centavos
        self.assertEqual(a_centavos(intento.monto_total), 5000000)
        respuesta = self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'APPROVED', 5000000))
        self.assertEqual(respuesta.data['codigo'], 'PAGO_CONFIRMADO')


class WebhookVerificacionApiTest(BasePagoAsincronoTest):
    """La reconsulta a la API de Wompi manda sobre el cuerpo del evento."""

    def test_api_contradice_al_cuerpo_y_gana_la_api(self):
        # El cuerpo dice APPROVED con firma valida, pero la API dice DECLINED.
        # Debe revertirse: la firma solo cubre los campos de 'properties', y la
        # respuesta de la API es la fuente autoritativa.
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        monto = a_centavos(intento.monto_total)
        evento = construir_evento(intento.idempotencia_clave, 'APPROVED', monto)
        api_dice = RespuestaPago(
            aprobada=False, transaccion_id='wompi-tx-1', estado='rechazado',
            pasarela='wompi', mensaje='Transaccion Wompi rechazado.',
            crudo={'id': 'wompi-tx-1', 'status': 'DECLINED',
                   'amount_in_cents': monto})

        respuesta = self.enviar_webhook(evento, verificada=api_dice)

        self.assertEqual(respuesta.data['codigo'], 'PAGO_REVERSADO')
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'rechazado')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 20)

    def test_api_confirma_y_se_registra_su_transaccion(self):
        self.iniciar_checkout(cantidad=2)
        intento = IntentoPago.objects.get(usuario=self.comprador)
        monto = a_centavos(intento.monto_total)
        api_dice = RespuestaPago(
            aprobada=True, transaccion_id='wompi-tx-real', estado='aprobado',
            pasarela='wompi', crudo={'id': 'wompi-tx-real',
                                     'status': 'APPROVED',
                                     'amount_in_cents': monto})

        respuesta = self.enviar_webhook(
            construir_evento(intento.idempotencia_clave, 'APPROVED', monto),
            verificada=api_dice)

        self.assertEqual(respuesta.data['codigo'], 'PAGO_CONFIRMADO')
        venta = Venta.objects.get(intento_pago=intento)
        self.assertEqual(venta.transaccion_id, 'wompi-tx-real')


# --------------------------- Estado del pago -------------------------------

class EstadoPagoTest(BasePagoAsincronoTest):
    """Endpoint que consulta el frontend al volver del Web Checkout."""

    def test_requiere_autenticacion(self):
        anonimo = APIClient()
        respuesta = anonimo.get("/api/tienda/pagos/estado/")
        self.assertIn(respuesta.status_code, (401, 403))

    def test_devuelve_pendiente_antes_del_webhook(self):
        _, intento = self.iniciar_checkout()
        respuesta = self.api().get(
            f"/api/tienda/pagos/estado/?referencia={intento.idempotencia_clave}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['estado'], 'pendiente')
        self.assertEqual(respuesta.data['ventas'][0]['total'], '50000.00')

    def test_devuelve_aprobado_despues_del_webhook(self):
        _, intento = self.iniciar_checkout()
        self.enviar_webhook(construir_evento(
            intento.idempotencia_clave, 'APPROVED',
            a_centavos(intento.monto_total)))
        respuesta = self.api().get(
            f"/api/tienda/pagos/estado/?referencia={intento.idempotencia_clave}")
        self.assertEqual(respuesta.data['estado'], 'aprobado')
        self.assertEqual(respuesta.data['transaccion_id'], 'wompi-tx-1')

    def test_referencia_inexistente(self):
        respuesta = self.api().get(
            "/api/tienda/pagos/estado/?referencia=no-existe")
        self.assertEqual(respuesta.status_code, 404)

    def test_no_expone_el_pago_de_otro_comprador(self):
        # Aislamiento: la referencia es adivinable a partir del carrito, asi
        # que la consulta tiene que estar acotada al usuario autenticado.
        _, intento = self.iniciar_checkout()
        intruso = User.objects.create_user(
            username="intruso@test.co", email="intruso@test.co",
            password="Clave12345")
        Perfil.objects.create(usuario=intruso, empresa=None,
                              rol=Rol.de_nombre("CLIENTE"))
        respuesta = self.api(intruso).get(
            f"/api/tienda/pagos/estado/?referencia={intento.idempotencia_clave}")
        self.assertEqual(respuesta.status_code, 404)
