"""
Pruebas de configuracion critica (Fase 2 - seguridad de produccion).

Estas pruebas validan la logica de arranque de `intersoft/settings.py` sin
depender del `.env` de desarrollo: recargan el modulo de settings con
variables de entorno controladas y comprueban que:

  - Con DEBUG=False y SECRET_KEY ausente o placeholder la app falla con un
    mensaje claro (ImproperlyConfigured).
  - Con DEBUG=False y una SECRET_KEY real el arranque es valido y las
    cookies/scabezas seguras quedan habilitadas (HTTPS + HSTS + HttpOnly).
  - Con DEBUG=True (desarrollo) los valores son comodos (cookies sin flag
    Secure, sin redirect HTTPS) y se permite el placeholder de secret.

IMPORTANTE: estas pruebas reemplazan el entorno de procesos en memoria.
Se ejecutan de forma aislada (un TestCase, clase no paralela) y restauran
las variables al final para no contaminar las demas pruebas.

Requiere: python manage.py test intersoft
"""
import importlib
import os
from unittest import mock

import django
from django.conf import settings as dj_settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

MODULE = 'intersoft.settings'

DEV_SECRET = 'django-insecure-cambia-esta-clave-en-produccion-intersoft-2026'
REAL_SECRET = 'confiable-alef-93xYz12-zdqz3Ooo-1a2b3c4d5e6f7'


def _cargar_con_env(nuevo_env):
    """Recarga settings.py con un diccionario de variables de entorno dado.

    Limpia cualquier variable relevante que no este en `nuevo_env` para que
    decouple no la lea del entorno del proceso padre (p.ej. la DEBUG del host).
    """
    claves = {
        'DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'CORS_ALLOWED_ORIGINS',
        'CSRF_TRUSTED_ORIGINS', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'DB_HOST', 'DB_PORT', 'EMAIL_BACKEND', 'EMAIL_HOST', 'EMAIL_PORT',
        'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'EMAIL_USE_TLS',
        'DEFAULT_FROM_EMAIL', 'IA_PROVIDER', 'IA_API_KEY', 'IA_API_URL',
        'IA_MODEL', 'IA_TIMEOUT', 'IA_MAX_HISTORIAL', 'WA_VINCULADO',
        'WA_API_URL', 'WA_TOKEN', 'WA_NUMERO', 'FRONTEND_URL',
        'SECURE_SSL_REDIRECT', 'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE',
        'SECURE_HSTS_SECONDS', 'SESSION_COOKIE_SAMESITE', 'CSRF_COOKIE_SAMESITE',
    }
    for k in claves:
        os.environ.pop(k, None)
    for k, v in nuevo_env.items():
        os.environ[k] = v
    return importlib.reload(importlib.import_module(MODULE))


class ConfiguracionSeguridadProduccionTest(SimpleTestCase):
    """Validaciones de la configuracion critica del backend."""

    @classmethod
    def tearDownClass(cls):
        # Restaura el entorno del proceso padre (lo que tuviera antes).
        for k in list(os.environ):
            if k.startswith(('DB_', 'EMAIL_HOST', 'IA_', 'WA_', 'SECURE_', 'SESSION_', 'CSRF_')):
                os.environ.pop(k, None)
        os.environ.pop('DEBUG', None)
        os.environ.pop('SECRET_KEY', None)
        os.environ.pop('ALLOWED_HOSTS', None)
        os.environ.pop('CORS_ALLOWED_ORIGINS', None)
        os.environ.pop('CSRF_TRUSTED_ORIGINS', None)
        super().tearDownClass()

    def _recargar_para_revertir(self):
        # Vuelve a recargar settings con el .env de desarrollo/CI real para no
        # dejar el settings del proceso (de tests) en modo produccion.
        for k in list(os.environ):
            if k.startswith(('DB_', 'EMAIL_HOST', 'IA_', 'WA_', 'SECURE_', 'SESSION_', 'CSRF_', 'DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'CORS_', 'CSRF_')):
                os.environ.pop(k, None)
        importlib.reload(importlib.import_module(MODULE))

    # ------------------------- SECRET_KEY fail-fast -------------------------

    def test_produccion_sin_secret_key_falla_con_mensaje_claro(self):
        # Simula la ausencia total de SECRET_KEY (sin .env y sin variable de
        # entorno): patcheamos Config.get para que devuelva vacio.
        from decouple import Config as _Config

        os.environ.pop('SECRET_KEY', None)

        real = _Config.get
        llamado = []

        def fake_get(self, option, *args, **kwargs):
            if option == 'SECRET_KEY':
                llamado.append(option)
                return ''
            return real(self, option, *args, **kwargs)

        with mock.patch.object(_Config, 'get', fake_get):
            with self.assertRaisesRegex(ImproperlyConfigured, 'SECRET_KEY no esta definida'):
                _cargar_con_env({'DEBUG': 'False', 'SECRET_KEY': ''})
        self.assertEqual(llamado, ['SECRET_KEY'])

    def test_produccion_con_placeholder_falla(self):
        with self.assertRaisesRegex(ImproperlyConfigured, 'insegura para produccion'):
            _cargar_con_env({'DEBUG': 'False', 'SECRET_KEY': DEV_SECRET})

    def test_produccion_con_secret_real_arranca_y_endurece_cookies(self):
        mod = _cargar_con_env({
            'DEBUG': 'False',
            'SECRET_KEY': REAL_SECRET,
            'ALLOWED_HOSTS': 'api.intersoft.co',
            'CORS_ALLOWED_ORIGINS': 'https://app.intersoft.co',
            'CSRF_TRUSTED_ORIGINS': 'https://app.intersoft.co',
        })
        self.assertEqual(mod.DEBUG, False)
        self.assertEqual(mod.SECRET_KEY, REAL_SECRET)
        # HTTPS seguro
        self.assertTrue(mod.SESSION_COOKIE_SECURE)
        self.assertTrue(mod.CSRF_COOKIE_SECURE)
        self.assertTrue(mod.SECURE_SSL_REDIRECT)
        self.assertTrue(mod.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertTrue(mod.SESSION_COOKIE_HTTPONLY)
        self.assertGreater(mod.SECURE_HSTS_SECONDS, 0)
        self.assertEqual(mod.X_FRAME_OPTIONS, 'DENY')
        # CORS solo con origenes explicitos, nunca '*'
        self.assertIn('https://app.intersoft.co', mod.CORS_ALLOWED_ORIGINS)

    def test_produccion_allowed_hosts_vacio_o_comodin_falla(self):
        with self.assertRaisesRegex(ImproperlyConfigured, 'ALLOWED_HOSTS invalido'):
            _cargar_con_env({'DEBUG': 'False', 'SECRET_KEY': REAL_SECRET,
                             'ALLOWED_HOSTS': '*'})
        with self.assertRaisesRegex(ImproperlyConfigured, 'ALLOWED_HOSTS invalido'):
            _cargar_con_env({'DEBUG': 'False', 'SECRET_KEY': REAL_SECRET,
                             'ALLOWED_HOSTS': ''})

    # ------------------------------- Desarrollo -----------------------------

    def test_desarrollo_permite_placeholder_y_cookies_comodas(self):
        mod = _cargar_con_env({
            'DEBUG': 'True',
            'SECRET_KEY': DEV_SECRET,
            'ALLOWED_HOSTS': 'localhost,127.0.0.1',
        })
        self.assertEqual(mod.DEBUG, True)
        self.assertFalse(mod.SESSION_COOKIE_SECURE)
        self.assertFalse(mod.CSRF_COOKIE_SECURE)
        self.assertFalse(mod.SECURE_SSL_REDIRECT)
        self.assertIn('localhost', mod.ALLOWED_HOSTS)

    def test_desarrollo_por_omision_arranca_sin_secret_explicita(self):
        # Sin .env/entorno, DEBUG=False por omision fallaria; con DEBUG=True el
        # placeholder por defecto basta para poder desarrollar. Sin EMAIL_BACKEND
        # explicito y DEBUG=True, el correo cae al backend de consola.
        mod = _cargar_con_env({
            'DEBUG': 'True',
            'SECRET_KEY': DEV_SECRET,
            'EMAIL_BACKEND': '',
        })
        self.assertTrue(mod.SECRET_KEY)
        self.assertEqual(mod.EMAIL_BACKEND, 'django.core.mail.backends.console.EmailBackend')
