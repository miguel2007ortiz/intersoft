#!/bin/bash
set -e

echo "Esperando a MySQL..."
until python -c "
import time, os, pymysql
for _ in range(30):
    try:
        pymysql.connect(
            host=os.getenv('DB_HOST','db'),
            port=int(os.getenv('DB_PORT','3306')),
            user=os.getenv('DB_USER','root'),
            password=os.getenv('DB_PASSWORD',''),
        )
        print('MySQL listo.')
        break
    except pymysql.err.OperationalError:
        time.sleep(2)
else:
    raise Exception('MySQL no estuvo disponible a tiempo.')
" 2>/dev/null; do
  sleep 2
done

echo "Ejecutando migraciones..."
python manage.py migrate --noinput

echo "Recolectando archivos estaticos..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Cargando roles del sistema..."
python manage.py seed_roles 2>/dev/null || true

echo "Iniciando servidor con gunicorn..."
exec gunicorn intersoft.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
