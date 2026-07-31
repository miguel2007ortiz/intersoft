"""
Configuración ASGI para InterSoft.
Expone la variable 'application' usada por servidores ASGI (Daphne, Uvicorn).
Útil para WebSockets en el futuro (notificaciones en tiempo real, cámaras).
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intersoft.settings')
application = get_asgi_application()
