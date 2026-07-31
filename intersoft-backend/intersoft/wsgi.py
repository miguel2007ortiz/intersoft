"""
Configuración WSGI para InterSoft.
Expone la variable 'application' usada por servidores WSGI (Gunicorn, uWSGI).
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intersoft.settings')
application = get_wsgi_application()
