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

# 4. Base de datos (crear una vez)
mysql -uroot -p -e "CREATE DATABASE intersoft1_db CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci; CREATE USER 'intersoft'@'localhost' IDENTIFIED BY '<password>'; GRANT ALL PRIVILEGES ON intersoft1_db.* TO 'intersoft'@'localhost'; FLUSH PRIVILEGES;"

# 5. Migraciones (si hay una BD existente: backup + migrate --plan primero)
python manage.py migrate

# 6. Datos demo (SOLO si no es produccion real)
python manage.py seed_demo

# 7. Verificacion
python manage.py check
python manage.py makemigrations --check --dry-run   # "No changes detected"
python manage.py test                               # 241 tests (opcional en prod)

# 8. WSGI en production
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

    location / {
        try_files $uri $uri/ /index.html;   # SPA fallback
    }
    location ~* \.(js|css|png|jpe?g|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Renovación Let's Encrypt: `sudo certbot --nginx`.

## 6. Checklist post-despliegue

- [ ] `curl -I https://api.tudominio.co/api/auth/me` → 401/403 (JWT exigido), no 500.
- [ ] `https://app.tudominio.co` carga la SPA y refresca con F5 en rutas internas.
- [ ] Login real OK; refrescar JWT OK; logout limpia cookies.
- [ ] Correr el checklist de seguridad (`docs/CHECKLIST-SEGURIDAD.md`).
- [ ] Backup de BD agendado + prueba de restore.