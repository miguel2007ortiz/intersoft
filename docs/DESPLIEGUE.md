# Guía de despliegue — InterSoft

Procedimiento de despliegue reproducible (estándar: Django REST + Angular SPA +
MySQL 8, detrás de nginx con HTTPS).

> Requisitos exactos y pasos de instalación también están en el
> `README.md` raíz. Esta guía asume un servidor Ubuntu/Debian (22.04+).

---

## 1. Requisitos del servidor

| Componente | Versión verificada | Notas |
|---|---|---|
| Python | **3.12.x** | `python3.12 --version` |
| Node.js | **24.x** (LTS) | solo para compilar el frontend |
| npm | 10.x/11.x | con `package-lock.json` |
| MySQL | **8.0** (8.0.36+) | `utf8mb4` / `utf8mb4_spanish_ci` |
| nginx | 1.24+ | proxy inverso + HTTPS |
| libmysqlclient-dev | — | para compilar `mysqlclient` (Ubuntu/Debian) |

## 2. Backend

```bash
# 1. Sistema (compilar mysqlclient)
sudo apt-get update
sudo apt-get install -y build-essential pkg-config default-libmysqlclient-dev python3.12-venv

# 2. Aplicacion
cd /srv/intersoft/backend
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt        # versiones PINNED

# 3. Entorno (plantilla; NUNCA versionar el .env real)
cp .env.example .env
#   - DEBUG=False
#   - SECRET_KEY=<aleatoria>          (generar con get_random_secret_key)
#   - ALLOWED_HOSTS=api.tudominio.co
#   - DB_* = credenciales MySQL
#   - CORS_ALLOWED_ORIGINS=https://app.tudominio.co
#   - CSRF_TRUSTED_ORIGINS=https://app.tudominio.co
#   - FRONTEND_URL=https://app.tudominio.co
#   - EMAIL_* / WA_* / IA_* segun corresponda
#   - BACKUP_DIR / MYSQLDUMP_BIN / MYSQL_BIN si necesitas fijar rutas del
#     respaldo (ver .env.example)

# 4. Base de datos (crear una vez)
mysql -uroot -p -e "CREATE DATABASE intersoft1_db CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci; CREATE USER 'intersoft'@'localhost' IDENTIFIED BY '<password>'; GRANT ALL PRIVILEGES ON intersoft1_db.* TO 'intersoft'@'localhost'; FLUSH PRIVILEGES;"

# 5. Migraciones (si hay una BD existente: backup + migrate --plan primero)
python manage.py migrate

# 6. Tabla del cache por base de datos (B1). Necesaria SIEMPRE que
#    CACHE_BACKEND sea el de BD (default). Idempotente.
python manage.py crear_cache

# 7. Datos demo (SOLO si no es produccion real)
python manage.py seed_demo

# 8. Verificacion
python manage.py check
python manage.py makemigrations --check --dry-run   # "No changes detected"
python manage.py test                               # 490 tests (opcional en prod)

# 9. WSGI en production
python manage.py collectstatic --noinput            # si Django sirve statics
```

## 3. Proceso WSGI (Gunicorn + systemd)

`/etc/systemd/system/intersoft.service`:

```ini
[Unit]
Description=InterSoft API (Django/gunicorn)
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/intersoft/backend
EnvironmentFile=/srv/intersoft/backend/.env
ExecStart=/srv/intersoft/backend/venv/bin/gunicorn \
  --access-logfile - --error-logfile - \
  -w 3 -b 127.0.0.1:8001 intersoft.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now intersoft
sudo systemctl status intersoft
```

> `DEBUG=False` + `SECURE_PROXY_SSL_HEADER` requieren que nginx envíe
> `X-Forwarded-Proto: https` (ver abajo).

## 4. Frontend (Angular)

```bash
cd /srv/intersoft/frontend
npm ci                                 # dependencias EXACTAS del lockfile
npm run build                          # genera dist/frontend (budgets activos)
npm run test:ci                        # Vitest (opcional en CI ya lo hace)

# Copia a donde nginx sirva la SPA:
sudo rsync -a --delete dist/frontend/browser/ /var/www/intersoft/
```

## 5. nginx (HTTPS)

```nginx
# Proxy del API
server {
    listen 443 ssl http2;
    server_name api.tudominio.co;

    ssl_certificate     /etc/letsencrypt/live/api.tudominio.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.tudominio.co/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;   # obligatorio (SECURE_SSL_REDIRECT)
    }
}

# SPA del frontend (con fallback para rutas del router Angular)
server {
    listen 443 ssl http2;
    server_name app.tudominio.co;
    root /var/www/intersoft;
    index index.html;

    ssl_certificate     /etc/letsencrypt/live/app.tudominio.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.tudominio.co/privkey.pem;

    # Content-Security-Policy de la SPA. connect-src incluye el dominio real
    # del API (si el frontend llama a https://api.tudominio.co/api) y hay que
    # ajustarlo al dominio real de produccion. style-src 'unsafe-inline' es
    # obligatorio (Angular inyecta estilos en runtime). La politica exacta es
    # la misma que emite el backend en /api (core/csp.py), sin las directivas
    # de conexion al API aqui repetidas por claridad.
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://api.tudominio.co; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        try_files $uri $uri/ /index.html;   # SPA fallback
    }
    location ~* \.(js|css|png|jpe?g|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";   # re-declarar cabeceras
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://api.tudominio.co; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
    }
    # Imagenes de productos (media del backend) servidas por este mismo
    # nginx para que img-src 'self' las permita.
    location /media/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Renovación Let's Encrypt: `sudo certbot --nginx`.

## 6. Backups y monitoreo (operativo)

```bash
# 1. Respaldo de la BD (consistente, sin bloquear escrituras). Con --verify
#    restaura el dump en una BD temporal, comprueba tablas y la elimina.
#    Nota: si mysqldump/mysql no estan en el PATH (p. ej. Laragon) fija
#    MYSQLDUMP_BIN/MYSQL_BIN en .env (ver .env.example).
python manage.py backup_db
python manage.py backup_db --verify   # prueba REAL de que el respaldo sirve

# 2. Chequeo de salud (exit 0 OK / exit 1 problema) — agendable con cron:
#    BD, migraciones al dia, cache, disco libre (min 1 GiB) y antiguedad
#    del ultimo respaldo (alerta > 24 h, configura en MONITOR_ALERTA_BACKUP_HORAS).
python manage.py monitor
```

Ejemplo de agendado (cron diario):

```cron
# Respaldo a las 02:00 y verificacion + monitor a las 02:30 (exit != 0 se loguea)
0 2 * * *  cd /srv/intersoft/backend && /srv/intersoft/backend/venv/bin/python manage.py backup_db >> /var/log/intersoft-backup.log 2>&1
30 2 * * * cd /srv/intersoft/backend && /srv/intersoft/backend/venv/bin/python manage.py monitor >> /var/log/intersoft-monitor.log 2>&1 || echo "MONITOR FALLO" >> /var/log/intersoft-monitor.log
```

> Los respaldos quedan en `BACKUP_DIR` (default `backend/backups/`, ignorado
> por git) con rotación automática (`BACKUP_RETENER_DIAS`, default 7). El
> checklist (`docs/CHECKLIST-SEGURIDAD.md`) obliga a probar el restore con
> `--verify` antes de confiar en un respaldo.

## 7. Checklist post-despliegue

- [ ] `curl -I https://api.tudominio.co/api/auth/me` → 401/403 (JWT exigido), no 500.
- [ ] `https://app.tudominio.co` carga la SPA y refresca con F5 en rutas internas.
- [ ] Login real OK; refrescar JWT OK; logout limpia cookies.
- [ ] Correr el checklist de seguridad (`docs/CHECKLIST-SEGURIDAD.md`).
- [ ] `python manage.py backup_db --verify` y `python manage.py monitor` en
      verde (exit 0) tras el primer despliegue; agendar ambos en cron.