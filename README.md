# InterSoft — Plataforma SaaS de gestión empresarial (multi-tenant)

Backend **Django REST + MySQL 8** y frontend **Angular** (SPA). Catálogo y
clientes, ventas/POS, inventario, facturación DIAN, dashboard y reportes,
asistente IA, notificaciones/cámaras y marketplace con carrito/checkout.

> Cierre de entrega (Fase 7): requisitos exactos, dependencias pinneadas,
> pipeline CI, checklist de seguridad/despliegue y resumen de riesgos en
> `docs/`.

---

## 1. Requisitos exactos

| Componente | Versión verificada | Instalación sugerida |
|---|---|---|
| **Python** | **3.12.x** (3.12.10 usado en desarrollo) | python.org o version manager |
| **Node.js** | **24.x** (LTS) — 24.15.0 usado | nodejs.org o `nvm install 24` |
| **npm** | 10.x/11.x | junto con Node |
| **MySQL** | **8.0** (8.0.36+) | Laragon (Windows) o MySQL Server |
| **Django** | `==5.2.17` (pinneado) | `pip install -r requirements.txt` |
| **Angular** | 22.x (CLI `^22.1`) | `npm ci` usa el `package-lock.json` |

No se requieren servicios externos para desarrollo: el asistente IA cae a un
**mock** local si no hay `IA_API_KEY`, el correo a la consola y WhatsApp se
desactiva con `WA_VINCULADO=False`.

## 2. Estructura del repositorio

```
.
├── backend/     Django REST Framework (API /api/*)
│   ├── core/    dominio (Empresa, Producto, Cliente, Venta, Facturacion…)
│   ├── cuentas/ autenticacion (/api/auth/*), RBAC, usuarios
│   └── intersoft/ proyecto (settings.py, urls)
├── frontend/    Angular SPA (panel admin + marketplace)
├── docs/        checklist de seguridad, despliegue y riesgos
└── .github/workflows/ci.yml   pipeline de integracion
```

## 3. Puesta en marcha — Backend

```bash
cd backend
python -m venv venv
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt     # versiones EXACTAS (reproducible)
```

**Entorno:** copia la plantilla y ajusta los valores (nunca se versiona el `.env`):
```bash
# Windows:  copy .env.example .env
# Mac/Linux: cp .env.example .env
```
Variables clave (todas documentadas en `backend/.env.example`):

| Variable | Producción |
|---|---|
| `SECRET_KEY` | **Obligatoria y aleatoria** (la app no arranca sin ella con `DEBUG=False`) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | dominios públicos reales, **sin** `*` |
| `DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT` | credenciales MySQL 8 |
| `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` | URL reales del frontend (HTTPS) |
| `EMAIL_HOST*` / `WA_TOKEN` / `IA_API_KEY` | credenciales reales, **nunca** en el repo |

**Base de datos, migraciones y demo:**
```bash
mysql -uroot -p -e "CREATE DATABASE intersoft1_db CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci;"
python manage.py migrate              # grafo completo (incluye merge + seed RBAC)
python manage.py seed_demo            # datos de demostracion (opcional)
python manage.py runserver            # http://127.0.0.1:8000
```

**Chequeos (mismos que corre el CI):**
```bash
python manage.py check
python manage.py makemigrations --check --dry-run   # "No changes detected"
python manage.py test                               # 241 tests
```

## 4. Puesta en marcha — Frontend

```bash
cd frontend
npm ci                    # dependencias EXACTAS del lockfile
npm run build             # dist/frontend (budgets: 500 kB initial)
npm run test:ci           # Vitest (20 tests, cobertura v8)
npm run start             # http://localhost:4200 (dev, apunta a :8000)
```

## 5. Pipeline CI (`.github/workflows/ci.yml`)

En cada push/PR a `main`/`develop` se ejecuta:

- **Frontend**: `npm ci` → `npm run lint` → `npm run build` → `npm run test:ci`.
- **Backend**: Python 3.12 + MySQL 8 (servicio) → `pip install -r requirements.txt`
  → `python manage.py check` → `python manage.py makemigrations --check --dry-run`
  → `python manage.py migrate` → `python manage.py test`.
- El job de backend corre con `DEBUG=False` y `SECRET_KEY`/`ALLOWED_HOSTS`
  explícitas, ejerciendo las protecciones de producción (fail-fast).

## 6. Documentación

| Documento | Contenido |
|---|---|
| `README.md` (raíz) | requisitos, arranque, decisiones de arquitectura (este archivo) |
| `backend/README.md` | backend en detalle: grafo de migraciones, fase 5 (solidez/errores/concurrencia), endpoints verificados |
| `frontend/README.md` | frontend: comandos y calidad (fase 6) |
| `docs/CHECKLIST-SEGURIDAD.md` | checklist de seguridad y despliegue |
| `docs/DESPLIEGUE.md` | guía de despliegue (gunicorn + nginx + HTTPS) |
| `docs/RIESGOS.md` | resumen de riesgos resueltos y pendientes |
| `AUDITORIA.md` | auditoría (solo lectura, fase previa) |

## 7. Decisiones de arquitectura

- **Multi-tenant**: tenancy por FK a `Empresa` + filtrado manual por vista
  (roles: `ADMINISTRADOR`, `EMPLEADO`, `CLIENTE` + roles personalizados por
  empresa; permisos finos `permiso.codigo`). Aislamiento verificado por tests.
- **Dashboard/reportes (fase 7)**: agregaciones vía **vistas SQL** en MySQL
  (`core/migrations/0006_dashboard_vistas.py` + `core/analytics.py`) en vez de
  MongoDB; frontend en SVG puro; exportación CSV/PDF sin dependencias extra.
- **Asistente IA (fase 8)**: `IA_PROVIDER=mock|groq|openai` con mock local sin
  internet; contexto de negocio desde las vistas; auditoría por consulta;
  `502` conserva la conversación para reintento sin duplicar.
- **Notificaciones y cámaras (fase 9)**: centro de notificaciones unificado
  con canal WhatsApp/email y reintento (`reintentar_notificaciones`); módulo de
  cámaras entregado como lienzo (sin streaming, ver `docs/RIESGOS.md`).
- **Seguridad de configuración**: con `DEBUG=False` la app **falla al arrancar**
  si `SECRET_KEY` es placeholder/ausente o `ALLOWED_HOSTS` incluye `*`;
  se activan solas `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, redirección
  HTTPS, HSTS y `X_FRAME_OPTIONS=DENY`.
- **Calidad (fases 5-6)**: errores de API uniformes `{codigo, detalle, errores}`,
  validación de entrada, paginación acotada, `select_for_update` en operaciones
  de dinero/stock, guards + permisos en frontend, helpers compartidos de
  errores y timers.