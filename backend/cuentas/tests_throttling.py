"""Throttling por IP en endpoints sensibles de autenticacion.

Cubre el pendiente n.º 1 de docs/RIESGOS.md: refresh, recuperacion de
contrasena y creacion de cuentas. Usa tasas pequenas via override_settings
para no depender de los limites reales de produccion y verifica el contrato
de errores {codigo, detalle, errores} en el 429.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Empresa

from .models import Perfil, Rol

REST_FRAMEWORK_TEST = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        'auth_refresh': '2/minute',
        'auth_recuperacion': '3/minute',
        'auth_registro': '4/minute',
    },
}


@override_settings(REST_FRAMEWORK=REST_FRAMEWORK_TEST)
class ThrottlingPorIPTest(APITestCase):
    """Verifica limites por IP y aislamiento por scope. Cada test limpia la
    cache (los buckets viven en LocMemCache durante los tests)."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Tienda Test", nit="900999999")
        user = User.objects.create_user(username="throttle@test.co",
                                        email="throttle@test.co",
                                        password="Clave12345")
        Perfil.objects.create(usuario=user, empresa=cls.empresa,
                              rol=Rol.de_nombre("EMPLEADO"))

    def setUp(self):
        cache.clear()

    def login(self):
        return self.client.post(reverse("auth-login"),
                                {"email": "throttle@test.co", "password": "Clave12345"},
                                content_type="application/json").json()

    def refresh(self, **extra):
        tokens = self.login()
        return self.client.post(reverse("auth-refresh"),
                                {"refresh": tokens["refresh"]},
                                content_type="application/json", **extra)

    def test_refresh_se_bloquea_desde_la_misma_ip(self):
        primera = self.refresh()
        segunda = self.refresh()
        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)

        bloqueada = self.refresh()
        self.assertEqual(bloqueada.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        # Contrato de errores de la API: {codigo, detalle, errores}.
        self.assertEqual(bloqueada.data["codigo"], "THROTTLED")
        self.assertIn("detalle", bloqueada.data)
        self.assertIn("errores", bloqueada.data)

    def test_ips_distintas_no_comparten_el_conteo(self):
        self.refresh()
        self.refresh()
        self.assertEqual(self.refresh().status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Otra IP (Django test client permite override de REMOTE_ADDR).
        desde_otra_ip = self.refresh(REMOTE_ADDR="192.168.1.50")
        self.assertEqual(desde_otra_ip.status_code, status.HTTP_200_OK)

    def test_scopes_son_independientes(self):
        self.refresh()
        self.refresh()
        self.assertEqual(self.refresh().status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Misma IP pero otro scope (recuperacion) sigue disponible.
        for _ in range(3):
            respuesta = self.client.post(reverse("auth-password-reset"),
                                         {"email": "throttle@test.co"})
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(reverse("auth-password-reset"),
                             {"email": "throttle@test.co"}).status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_recuperacion_y_registro_tambien_se_bloquean(self):
        for _ in range(3):
            self.client.post(reverse("auth-password-reset"), {"email": "a@test.co"})
        self.assertEqual(
            self.client.post(reverse("auth-password-reset"),
                             {"email": "a@test.co"}).status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        for _ in range(4):
            self.client.post(reverse("auth-registro"), {"email": "nuevo@test.co"})
        self.assertEqual(self.client.post(reverse("auth-registro"),
                                          {"email": "nuevo@test.co"}).status_code,
                         status.HTTP_429_TOO_MANY_REQUESTS)

    def test_xff_spoof_no_evade_el_throttle(self):
        self.refresh()
        self.refresh()

        # Detras de nginx la IP confiable es la ULTIMA de X-Forwarded-For:
        # un prefijo falseado no da un bucket nuevo.
        con_cabecera_falsa = self.refresh(
            HTTP_X_FORWARDED_FOR="8.8.8.8, 127.0.0.1",
        )
        self.assertEqual(con_cabecera_falsa.status_code,
                         status.HTTP_429_TOO_MANY_REQUESTS)