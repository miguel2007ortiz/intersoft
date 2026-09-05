"""Pruebas del notificador (core/services/notificador.py).

Cubre la logica de seleccion de canal sin tocar la base de datos:
- WhatsApp vinculado correcto -> canal 'whatsapp'.
- WhatsApp no vinculado / sin token / sin numero / HTTP fallido
  -> cae al canal email (o 'ninguno' si tampoco hay email).
- Email fallido -> 'ninguno'.
- Sin destinatarios -> 'ninguno'.
- Envio por email exitoso -> 'email'.
"""

import json
import urllib.parse
import urllib.request
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from .services import notificador
from .services.notificador import entregar, enviar_whatsapp


class WhatsAppNoDisponibleTest(SimpleTestCase):
    @override_settings(WA_VINCULADO=False, WA_TOKEN="token")
    def test_no_vinculado_levanta_excepcion(self):
        with self.assertRaises(notificador.WhatsAppNoDisponible):
            enviar_whatsapp("573001112233", "hola")

    @override_settings(WA_VINCULADO=True, WA_TOKEN="", WA_NUMERO="573000")
    def test_sin_token_levanta_excepcion(self):
        with self.assertRaises(notificador.WhatsAppNoDisponible):
            enviar_whatsapp("573001112233", "hola")

    @override_settings(WA_VINCULADO=True, WA_TOKEN="abc", WA_NUMERO="")
    def test_sin_numero_remitente_levanta_excepcion(self):
        with self.assertRaises(notificador.WhatsAppNoDisponible):
            enviar_whatsapp("573001112233", "hola")


class WhatsAppOkTest(SimpleTestCase):
    @override_settings(
        WA_VINCULADO=True,
        WA_TOKEN="abc123",
        WA_NUMERO="573000111",
        WA_API_URL="https://graph.example.test/v20.0/",
    )
    @patch("urllib.request.urlopen")
    def test_envia_payload_correcto(self, mock_urlopen):
        mock_resp = mock_urlopen.return_value.__enter__.return_value
        mock_resp.status = 200
        resultado = enviar_whatsapp("573001112233", "mensaje")
        self.assertEqual(resultado, 1)

        req = mock_urlopen.call_args.args[0]
        self.assertIsInstance(req, urllib.request.Request)
        self.assertEqual(req.full_url, "https://graph.example.test/v20.0/messages")
        self.assertEqual(req.headers["Authorization"], "Bearer abc123")

        data = urllib.parse.parse_qs(req.data.decode()) if hasattr(req.data, "decode") else {}
        payload = json.loads(data["data"][0])
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["to"], "573001112233")
        self.assertEqual(payload["text"]["body"], "mensaje")

    @override_settings(
        WA_VINCULADO=True,
        WA_TOKEN="abc123",
        WA_NUMERO="573000111",
        WA_API_URL="https://graph.example.test/v20.0/",
    )
    @patch("urllib.request.urlopen")
    def test_http_5xx_levanta_excepcion(self, mock_urlopen):
        mock_resp = mock_urlopen.return_value.__enter__.return_value
        mock_resp.status = 503
        with self.assertRaises(notificador.WhatsAppNoDisponible):
            enviar_whatsapp("573001112233", "mensaje")

    @override_settings(
        WA_VINCULADO=True,
        WA_TOKEN="abc123",
        WA_NUMERO="573000111",
        WA_API_URL="https://graph.example.test/v20.0/",
    )
    @patch("urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_fallo_red_levanta_excepcion(self, mock_urlopen):
        with self.assertRaises(notificador.WhatsAppNoDisponible):
            enviar_whatsapp("573001112233", "mensaje")


class EmailTest(SimpleTestCase):
    @override_settings(DEBUG=False, DEFAULT_FROM_EMAIL="no-reply@test.co")
    @patch("django.core.mail.send_mail")
    def test_email_exitoso_devuelve_1(self, mock_send):
        mock_send.return_value = 1
        resultado = notificador.enviar_email("cliente@test.co", "hola")
        self.assertEqual(resultado, 1)
        mock_send.assert_called_once_with(
            subject="Notificacion InterSoft",
            message="hola",
            from_email="no-reply@test.co",
            recipient_list=["cliente@test.co"],
            fail_silently=settings.DEBUG,
        )

    @override_settings(DEBUG=False, DEFAULT_FROM_EMAIL="no-reply@test.co")
    @patch("django.core.mail.send_mail", side_effect=Exception("smtp down"))
    def test_email_fallido_devuelve_0(self, mock_send):
        resultado = notificador.enviar_email("cliente@test.co", "hola")
        self.assertEqual(resultado, 0)


class EntregarTest(SimpleTestCase):
    @override_settings(
        WA_VINCULADO=True,
        WA_TOKEN="abc",
        WA_NUMERO="573000111",
        WA_API_URL="https://graph.example.test/v20.0/",
    )
    @patch("core.services.notificador.enviar_whatsapp")
    def test_whatsapp_es_el_canal_efectivo(self, mock_wa):
        mock_wa.return_value = 1
        canal = entregar("hola", destino_whatsapp="573001112233", destino_email="x@test.co")
        self.assertEqual(canal, "whatsapp")

    @override_settings(WA_VINCULADO=False, WA_TOKEN="")
    @patch("core.services.notificador.enviar_email", return_value=1)
    def test_cae_a_email_cuando_whatsapp_no_esta(self, mock_email):
        canal = entregar("hola", destino_whatsapp="573001112233", destino_email="x@test.co")
        self.assertEqual(canal, "email")
        mock_email.assert_called_once()

    @override_settings(WA_VINCULADO=False, WA_TOKEN="")
    @patch("core.services.notificador.enviar_email", return_value=0)
    def test_ninguno_si_email_tambien_falla(self, mock_email):
        canal = entregar("hola", destino_whatsapp="573001112233", destino_email="x@test.co")
        self.assertEqual(canal, "ninguno")

    @override_settings(WA_VINCULADO=False, WA_TOKEN="")
    def test_ninguno_sin_destinatarios(self):
        canal = entregar("hola")
        self.assertEqual(canal, "ninguno")

    @override_settings(WA_VINCULADO=True, WA_TOKEN="abc", WA_NUMERO="573000111")
    @patch("core.services.notificador.enviar_whatsapp", side_effect=notificador.WhatsAppNoDisponible("x"))
    @patch("core.services.notificador.enviar_email", return_value=1)
    def test_whatsapp_falla_y_email_cubre(self, mock_email, mock_wa):
        canal = entregar("hola", destino_whatsapp="573001112233", destino_email="y@test.co")
        self.assertEqual(canal, "email")

    @override_settings(WA_VINCULADO=True, WA_TOKEN="abc", WA_NUMERO="573000111")
    @patch("core.services.notificador.enviar_whatsapp", side_effect=notificador.WhatsAppNoDisponible("x"))
    def test_sin_email_devuelve_ninguno(self, mock_wa):
        canal = entregar("hola", destino_whatsapp="573001112233")
        self.assertEqual(canal, "ninguno")