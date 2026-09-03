# =====================================================================
#  InterSoft - Backend (Django REST) en contenedor.
#  Base: Python 3.12 (slim) con soporte de compilacion para mysqlclient.
#  En produccion sirve con Gunicorn y aplica migraciones en el arranque.
# =====================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencias del sistema necesarias para compilar mysqlclient
# (PyMySQL es el fallback puro-Python, pero mysqlclient da mejor rendimiento).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar primero solo las dependencias (mejor capa de cache).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo de la aplicacion.
COPY . .

# Directorio donde se escribira la config/cache de arranque.
RUN mkdir -p /app/logs /app/staticfiles /app/media

EXPOSE 8000

# Entrypoint: espera la BD, migra, colecta estaticos y sirve con Gunicorn.
CMD ["sh", "-c", \
     "until python manage.py migrate --noinput 2>/dev/null; do echo 'Esperando BD...'; sleep 3; done; \
      python manage.py collectstatic --noinput && \
      gunicorn intersoft.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
