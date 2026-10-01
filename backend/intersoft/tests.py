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

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

MODULE = 'intersoft.settings'

DEV_SECRET = 'django-insecure-cambia-esta-clave-en-produccion-intersoft-2026'
REAL_SECRET = 'confiable-alef-93xYz12-zdqz3Ooo-1a2b3c4d5e6f7'

# Todas las variables que tocan estas pruebas. `_snapshot_env`/`_restaurar_env`
# trabajan sobre este set para que el revert siempre devuelva el entorno con el
# que arranco la clase (DEBUG/SECRET_KEY/ALLOWED_HOSTS incluidos), tambien en CI
# donde no existe un fichero `.env` y decouple solo lee el entorno real.
CLAVES_ENV = {
    'DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'CORS_ALLOWED_ORIGINS',
    'CSRF_TRUSTED_ORIGINS', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
    'DB_HOST', 'DB_PORT', 'EMAIL_BACKEND', 'EMAIL_HOST', 'EMAIL_PORT',
    'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'EMAIL_USE_TLS',
    'DEFAULT_FROM_EMAIL', 'IA_PROVIDER', 'IA_API_KEY', 'IA_API_URL',
    'IA_MODEL', 'IA_TIMEOUT', 'IA_MAX_HISTORIAL', 'WA_VINCULADO',
    'WA_API_URL', 'WA_TOKEN', 'WA_NUMERO', 'FRONTEND_URL',
    'SECURE_SSL_REDIRECT', 'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE',
    'SECURE_HSTS_SECONDS', 'SESSION_COOKIE_SAMESITE', 'CSRF_COOKIE_SAMESITE',
    'CACHE_BACKEND', 'CACHE_LOCATION', 'NUM_PROXIES',
}


def _snapshot_env():
    """Devuelve un dict `{clave: valor|None}` con el entorno actual.

    `None` significa que la clave estaba ausente, para poder restaurar tanto
    las claves presentes como eliminar las que no existian al hacer el snapshot.
    """
    return {k: os.environ.get(k) for k in CLAVES_ENV}


def _restaurar_env(snapshot):
    """Devuelve os.environ exactamente al estado capturado en `snapshot`."""
    for k, v in snapshot.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _cargar_con_env(nuevo_env):
    """Recarga settings.py con un diccionario de variables de entorno dado.

    Limpia cualquier variable relevante que no este en `nuevo_env` para que
    decouple no la lea del entorno del proceso padre (p.ej. la DEBUG del host).
    """
    for k in CLAVES_ENV:
        os.environ.pop(k, None)
    for k, v in nuevo_env.items():
        os.environ[k] = v
    return importlib.reload(importlib.import_module(MODULE))


class ConfiguracionSeguridadProduccionTest(SimpleTestCase):
    """Validaciones de la configuracion critica del backend."""

    @classmethod
    def setUpClass(cls):
        # Guarda el entorno con el que arranco la clase (DEBUG/SECRET_KEY
        # incluidos). Sin este snapshot el revert no tiene a que volver: en CI
        # no hay `.env` y `_recargar_para_revertir` dejaba el settings sin
        # SECRET_KEY/DEBUG -> el fail-fast tiraba 9 errores en cada push.
        cls._ENV_ORIGINAL = _snapshot_env()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Restaura el entorno del proceso padre (lo que tuviera antes).
        _restaurar_env(cls._ENV_ORIGINAL)
        super().tearDownClass()

    def _recargar_para_revertir(self):
        # Devuelve el entorno al estado con el que arranco la clase (re-inyecta
        # DEBUG/SECRET_KEY/ALLOWED_HOSTS y elimina los valores que las pruebas
        # dejaron) y recarga settings para no dejar el modulo en modo
        # produccion. En CI sin `.env` el reload solo es valido si SECRET_KEY y
        # DEBUG vuelven a estar presentes antes de reimportar.
        _restaurar_env(type(self)._ENV_ORIGINAL)
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


    # --------------------- BUG-18: nada interno con DEBUG=False -------------

    def test_produccion_rechaza_las_claves_publicas_del_repo(self):
        """Los valores que el repo trae versionados son publicos y no pueden
        valer para produccion aunque no lleven el prefijo django-insecure-:
        el de `.env.example` y el del `docker-compose.yml`."""
        for clave in ('cambia-esta-clave-en-produccion-intersoft-2026',
                      'docker-local-secret-cambiar-en-produccion-2026'):
            with self.assertRaisesRegex(ImproperlyConfigured,
                                        'insegura para produccion'):
                _cargar_con_env({'DEBUG': 'False', 'SECRET_KEY': clave})
        self._recargar_para_revertir()

    def test_produccion_solo_renderiza_json(self):
        """El BrowsableAPIRenderer publica formularios y nombres de campos de
        los serializers: util en desarrollo, mapa del backend en produccion."""
        mod = _cargar_con_env({
            'DEBUG': 'False',
            'SECRET_KEY': REAL_SECRET,
            'ALLOWED_HOSTS': 'api.intersoft.co',
        })
        renderers = mod.REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES']
        self.assertEqual(tuple(renderers),
                         ('rest_framework.renderers.JSONRenderer',))
        self._recargar_para_revertir()

    def test_desarrollo_conserva_el_navegador_de_la_api(self):
        mod = _cargar_con_env({'DEBUG': 'True'})
        self.assertIn('rest_framework.renderers.BrowsableAPIRenderer',
                      mod.REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'])
        self._recargar_para_revertir()

    def test_debug_por_defecto_es_false_si_falta_la_variable(self):
        """Un despliegue que olvide definir DEBUG arranca cerrado."""
        from decouple import Config as _Config

        real = _Config.get

        def sin_debug(self, option, *args, **kwargs):
            if option == 'DEBUG':
                # `default` es el segundo posicional o va por kwargs.
                if args:
                    return args[0]
                return kwargs.get('default')
            return real(self, option, *args, **kwargs)

        with mock.patch.object(_Config, 'get', sin_debug):
            with self.assertRaisesRegex(ImproperlyConfigured, 'SECRET_KEY'):
                _cargar_con_env({'SECRET_KEY': ''})
        self._recargar_para_revertir()


    # ----------------- Fase 2.2 p2: cache segun entorno --------------------

    def test_produccion_usa_cache_compartido_por_omision(self):
        """Del cache cuelgan los contadores del throttling y del bloqueo de
        login: con DEBUG=False tiene que ser compartido entre procesos."""
        mod = _cargar_con_env({
            'DEBUG': 'False',
            'SECRET_KEY': REAL_SECRET,
            'ALLOWED_HOSTS': 'api.intersoft.co',
        })
        # Bajo el runner de tests `CACHES` se fuerza a LocMem al final del
        # settings para aislar las corridas, asi que lo que describe la
        # decision del entorno es `CACHE_BACKEND`.
        self.assertEqual(mod.CACHE_BACKEND,
                         'django.core.cache.backends.db.DatabaseCache')
        self._recargar_para_revertir()

    def test_el_backend_por_omision_depende_de_debug(self):
        """Sin CACHE_BACKEND en el entorno, el valor por omision lo decide
        DEBUG. Se parchea `Config.get` porque el `.env` de desarrollo define la
        variable y `_cargar_con_env` solo limpia os.environ, no el fichero."""
        from decouple import Config as _Config

        real = _Config.get

        def sin_cache_backend(self, option, *args, **kwargs):
            if option == 'CACHE_BACKEND':
                return args[0] if args else kwargs.get('default')
            return real(self, option, *args, **kwargs)

        with mock.patch.object(_Config, 'get', sin_cache_backend):
            local = _cargar_con_env({'DEBUG': 'True'})
            self.assertEqual(local.CACHE_BACKEND,
                             'django.core.cache.backends.locmem.LocMemCache')

            produccion = _cargar_con_env({
                'DEBUG': 'False',
                'SECRET_KEY': REAL_SECRET,
                'ALLOWED_HOSTS': 'api.intersoft.co',
            })
            self.assertEqual(produccion.CACHE_BACKEND,
                             'django.core.cache.backends.db.DatabaseCache')
        self._recargar_para_revertir()

    def test_produccion_con_locmem_no_arranca(self):
        """LocMemCache es por proceso: con varios workers cada uno llevaria su
        propio contador y el limite por IP se multiplicaria en silencio."""
        with self.assertRaisesRegex(ImproperlyConfigured, 'LocMemCache no sirve'):
            _cargar_con_env({
                'DEBUG': 'False',
                'SECRET_KEY': REAL_SECRET,
                'ALLOWED_HOSTS': 'api.intersoft.co',
                'CACHE_BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            })
        self._recargar_para_revertir()

    def test_produccion_acepta_redis(self):
        mod = _cargar_con_env({
            'DEBUG': 'False',
            'SECRET_KEY': REAL_SECRET,
            'ALLOWED_HOSTS': 'api.intersoft.co',
            'CACHE_BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'CACHE_LOCATION': 'redis://127.0.0.1:6379/1',
        })
        self.assertEqual(mod.CACHE_BACKEND,
                         'django.core.cache.backends.redis.RedisCache')
        self._recargar_para_revertir()

    def test_num_proxies_se_lee_del_entorno_y_por_omision_es_cero(self):
        por_omision = _cargar_con_env({'DEBUG': 'True'})
        self.assertEqual(por_omision.REST_FRAMEWORK['NUM_PROXIES'], 0)
        self._recargar_para_revertir()

        detras_de_nginx = _cargar_con_env({'DEBUG': 'True', 'NUM_PROXIES': '1'})
        self.assertEqual(detras_de_nginx.REST_FRAMEWORK['NUM_PROXIES'], 1)
        self._recargar_para_revertir()

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
