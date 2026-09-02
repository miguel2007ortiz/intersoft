"""
Configuracion de Django para el proyecto InterSoft.

Plataforma SaaS de gestion empresarial multi-tenant.
Base de datos: MySQL 8
"""

from datetime import timedelta
from pathlib import Path
from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config('DEBUG', default=False, cast=bool)

# ---------------------------------------------------------------- SECRET_KEY
# En produccion (DEBUG=False) la clave debe venir SIEMPRE de SECRET_KEY y no
# puede ser el placeholder de desarrollo. Fail-fast: si falta o es el marcador
# claro, la app no arranca con un mensaje accionable en vez de fallar a mitad
# de camino o usar una clave predecible (riesgo de firmar tokens falsos).
_SECRET_KEY = config('SECRET_KEY', default='')
_DEV_SECRET_PLACEHOLDER = 'django-insecure-cambia-esta-clave-en-produccion-intersoft-2026'
if not DEBUG:
    if not _SECRET_KEY:
        raise ImproperlyConfigured(
            'SECRET_KEY no esta definida. Con DEBUG=False debes definir '
            'SECRET_KEY en el entorno (ver backend/.env.example). Genera una '
            "segura con: python -c \"from django.core.management.utils import "
            "get_random_secret_key; print(get_random_secret_key())\""
        )
    if _SECRET_KEY == _DEV_SECRET_PLACEHOLDER or _SECRET_KEY.startswith('django-insecure-'):
        raise ImproperlyConfigured(
            'SECRET_KEY insegura para produccion: no uses el valor de '
            'desarrollo (django-insecure-*) ni placeholders. Define una clave '
            'aleatoria nueva en el entorno (ver backend/.env.example).'
        )

# En desarrollo permitimos el placeholder comodo; en cualquier entorno
# compartido (DEBUG=False) ya se valido arriba que la clave sea real.
SECRET_KEY = _SECRET_KEY or _DEV_SECRET_PLACEHOLDER

# ------------------------------------------------------------ ALLOWED_HOSTS
# En produccion debe declararse explícitamente el/los dominios/ips publicos.
# Si no se configura (DEBUG=False) fallamos temprano para evitar el riesgo de
# cabecera de host (DNS rebinding / Host header attacks) al arrancar con '*' .
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)
if not DEBUG and (not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS invalido para produccion: debe listar los dominios '
        'publicos del despliegue separados por comas (sin "*"). '
        'Ej: ALLOWED_HOSTS=api.intersoft.co,www.mitienda.com'
    )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'core',       # dominio de negocio (Empresa, Producto, Cliente, Venta)
    'cuentas',    # autenticacion: API /api/auth/* consumida por Angular
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',   # antes de CommonMiddleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'cuentas.middleware.CambioPasswordMiddleware',  # bloqueo por password pendiente (fase Empleados)
    'cuentas.middleware.AuditoriaMiddleware',  # auditoria de escrituras (fase 1)
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'intersoft.urls'
WSGI_APPLICATION = 'intersoft.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

# -- Base de datos - MySQL 8 (Laragon) ------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='intersoft1_db'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'core.exceptions.manejador_excepciones',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:4200,http://127.0.0.1:4200',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# --------------------------------------------------------- CORS / CSRF (prod)
# En desarrollo el frontend corre en http://localhost:4200. En produccion
# debe configurarse CORS_ALLOWED_ORIGINS con el/los origen/es reales y
# CSRF_TRUSTED_ORIGINS con los mismos (para peticiones con cookies).
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default=CORS_ALLOWED_ORIGINS[0] if CORS_ALLOWED_ORIGINS else '',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()] if v else [],
)

# ------------------------------------------- Seguridad HTTP / cookies (prod)
# Con DEBUG=False se endurece la config de cookies de sesion/CSRF y las
# cabeceras de seguridad (HTTPS). En desarrollo se dejan los valores comodos
# para servir sobre http://localhost sin friccion.
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 anno
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Sesion segura por cookies y nombre de cookie razonable.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Angular debe leer el token CSRF via JS

# El campo de cookie es razonablemente estricto por omision.
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Lax')
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Lax')

# Prohibir nuestra API dentro de iframes ajenos (clickjacking).
X_FRAME_OPTIONS = 'DENY'

MAX_INTENTOS_LOGIN = 5
MINUTOS_BLOQUEO = 15

FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:4200')

# -- Correo (fase 9) ----------------------------------------------
# Configurable por variables de entorno. Si no se define EMAIL_BACKEND:
#  - DEBUG=True  -> consola (no envia, ideal para desarrollo)
#  - DEBUG=False -> SMTP real (requiere EMAIL_HOST/USER/PASSWORD)
# Al definir EMAIL_BACKEND de forma explicita se fuerza un backend concreto.
if config('EMAIL_BACKEND', default=''):
    EMAIL_BACKEND = config('EMAIL_BACKEND')
elif DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-responder@intersoft.co')

# -- Asistente IA (fase 8) ---------------------------------------
# Proveedor configurable por variables de entorno. Si no se define
# IA_API_KEY, el sistema usa un "mock" local (sin conexion externa).
IA_PROVIDER = config('IA_PROVIDER', default='mock')
IA_API_KEY = config('IA_API_KEY', default='')
IA_API_URL = config('IA_API_URL', default='')
IA_MODEL = config('IA_MODEL', default='gpt-3.5-turbo')
IA_TIMEOUT = config('IA_TIMEOUT', default=20, cast=int)
# Limite de mensajes de historial que se envian al motor por turno.
IA_MAX_HISTORIAL = config('IA_MAX_HISTORIAL', default=10, cast=int)

# -- Notificaciones (fase 9) --------------------------------------
# Si WA_VINCULADO es False (o la llamada a la API falla), el notificador
# cae en el canal alterno (email). Con settings de test el email va a
# la consola de Django (locmem), sin conexion externa.
WA_VINCULADO = config('WA_VINCULADO', default=False, cast=bool)
WA_API_URL = config('WA_API_URL', default='https://graph.facebook.com/v18.0/')
WA_TOKEN = config('WA_TOKEN', default='')
# Número de teléfono del remitente (WhatsApp Business). Se usa como "from"
# en la peticion a la API; si no esta configurado no se puede enviar.
WA_NUMERO = config('WA_NUMERO', default='')

# -- Logging -----------------------------------------------------
# Con DEBUG=False, Django ya no muestra tracebacks ni datos de
# conexion en el navegador; los errores quedan registrados aqui
# para que el equipo los pueda revisar sin exponerlos al publico.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'intersoft.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
