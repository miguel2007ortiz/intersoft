"""
Configuración de Django para el proyecto InterSoft.

Plataforma SaaS de gestión empresarial multi-tenant.
Base de datos: MySQL 8
SENA ADSO 2026 — Daniel Velasco, Miguel Ortiz
"""

from pathlib import Path
from decouple import config

# ════════════════════════════════════════════════════════════
# RUTAS BASE
# ════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════
# SEGURIDAD
# ════════════════════════════════════════════════════════════
# La SECRET_KEY se lee desde el archivo .env (NUNCA subir a Git)
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-cambia-esta-clave-en-produccion-intersoft-2026'
)

# DEBUG = True solo en desarrollo. En producción debe ser False.
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [s.strip() for s in v.split(',')]
)


# ════════════════════════════════════════════════════════════
# APLICACIONES INSTALADAS
# ════════════════════════════════════════════════════════════
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Librerías de terceros
    'rest_framework',

    # Apps propias
    'core',
]


# ════════════════════════════════════════════════════════════
# MIDDLEWARE (orden importa)
# ════════════════════════════════════════════════════════════
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'intersoft.urls'


# ════════════════════════════════════════════════════════════
# TEMPLATES
# ════════════════════════════════════════════════════════════
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # templates globales (opcional)
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'intersoft.wsgi.application'


# ════════════════════════════════════════════════════════════
# BASE DE DATOS — MySQL 8
# ════════════════════════════════════════════════════════════
# Las credenciales se leen del archivo .env para mayor seguridad.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='intersoft_db'),
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


# ════════════════════════════════════════════════════════════
# VALIDADORES DE CONTRASEÑA
# ════════════════════════════════════════════════════════════
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ════════════════════════════════════════════════════════════
# INTERNACIONALIZACIÓN (Colombia)
# ════════════════════════════════════════════════════════════
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# ════════════════════════════════════════════════════════════
# ARCHIVOS ESTÁTICOS Y MEDIA
# ════════════════════════════════════════════════════════════
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ════════════════════════════════════════════════════════════
# OTROS
# ════════════════════════════════════════════════════════════
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ════════════════════════════════════════════════════════════
# AUTENTICACIÓN — redirecciones
# ════════════════════════════════════════════════════════════
# A dónde mandar si un usuario no autenticado entra a una página protegida
LOGIN_URL = 'core:login'
# A dónde ir tras iniciar sesión
LOGIN_REDIRECT_URL = 'core:dashboard'
# A dónde ir tras cerrar sesión
LOGOUT_REDIRECT_URL = 'core:login'

# Django REST Framework (configuración base)
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
