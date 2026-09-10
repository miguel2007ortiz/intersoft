# AUDITORÍA DEL PROYECTO — InterSoft (solo lectura)

Fecha: 2026-09-03. Rama: `prueba_tecnica`. Alcance: `backend/` (Django REST) y `frontend/` (Angular). No se modificó, creó ni borró ningún archivo salvo este reporte.

> **Nota de revisor:** este documento ACTUALIZA la auditoría anterior (2026-08-25), que describía un estado ya superado. Esta versión refleja el estado real del repositorio a la fecha, e **indica expresamente qué hallazgos previos fueron corregidos** (sección 10). La raíz no contiene `SPEC.md`; la arquitectura es **frontend/backend separados** (SPA Angular + API REST pura), no un Django monolítico con render server-side.

---

## 1. Stack y configuración

- **Backend:** Django 5.2.17, DRF 3.18.0, SimpleJWT 5.5.1, cors-headers 4.9.0, python-decouple 3.8, Pillow 11.2.1. Conectores MySQL: `mysqlclient==2.2.8` (Linux/CI) con fallback automático a `PyMySQL==1.1.0` en Windows (`backend/intersoft/__init__.py`). Versiones **pinneadas** (`==`) en `backend/requirements.txt`, reproducibles.
- **Python:** 3.12.x (verificado en desarrollo y CI; el `ci.yml` usa `python-version: '3.12'`).
- **Servidor de producción:** `gunicorn==23.0.0` (usado por el contenedor Docker).
- **Facturación DIAN:** `reportlab==5.0.1`, `lxml==6.1.3`, `zeep==4.3.3` (cliente SOAP 1.2).
- **Frontend:** Angular 22 (CLI `^22.1`), TypeScript `~6.0.2`, Vitest 4 (jsdom, cobertura v8), Prettier 3. Dependencias con `^`/`~` en `package.json` (el *lockfile* es el que fija versiones exactas; `npm ci`).
- **Dev de backend:** `requirements-dev.txt` (ruff 0.8.4, bandit 1.8.3, coverage 7.6.9) — instalados solo en CI/local, no en producción.
- **Docker:** `docker-compose.yml` con MySQL 8, Redis 7, backend (Gunicorn) y frontend (nginx + proxy de `/api` y `/media`). El proxy usa **rutas relativas** (build arg `API_URL=/api`), así la SPA sirve API y media desde el mismo origen en contenedor.
- **Cache:** `CACHES` por defecto es `DatabaseCache`; configurable a Redis con `CACHE_BACKEND`/`CACHE_LOCATION` (ver `docker-compose.yml:66-67`). En tests se fuerza `LocMemCache` (`settings.py:150-154`).
- **i18n:** `LANGUAGE_CODE='es-co'`, `TIME_ZONE='America/Bogota'`.

---

## 2. Multi-tenancy

- **Mecanismo:** tenancy por **Foreign Key a `Empresa`** + **filtrado manual por vista** (no hay `django-tenants`, ni schemas, ni middleware de resolución de subdominio).
- **Tenant:** `Empresa` (`core/models.py:27-58`) con `nit` único, `slug` único (autogenerado), `plan` (basic/pro/enterprise) y `activa`.
- **Resolución:** cada vista lee `request.user.perfil.empresa` (el `Perfil` ata usuario↔empresa en `cuentas/models.py`).
- **Modelos globales vs. por empresa:** los roles base (ADMINISTRADOR/EMPLEADO/CLIENTE) son **globales** (`Rol.empresa=None`); todo lo demás cuelga de `Empresa` (`Categoria`, `Producto`, `Cliente`, `Venta`, `Cupon`, `Camara`, `Notificacion`, …).
- **Alcances que NO son por empresa (intencionales como marketplace multi-vendedor):**
  - `Cliente.empresa` puede ser `None` para compradores del marketplace (`models.py:160-161`); `Perfil.empresa` puede ser `None` para el rol CLIENTE/comprador.
  - Carrito, favoritos y comentarios son por **usuario**, no por empresa vendedora (un comprador agrega productos de varias empresas).
  - El checkout agrupa items por empresa vendedora y genera una venta por cada una.
- **Aislamiento verificado por código y tests:** los `APIView` filtran con `.filter(empresa=...)` o vía `roles_visibles(empresa)` (sección 3). Existe `core/tests_aislamiento.py` (28 tests) con **dos empresas** (A y B) que comprueban que un tenant no ve/modifica datos ajenos (productos, clientes, ventas, POS, inventario, roles).

---

## 3. Usuarios y RBAC

- **Modelo de usuario:** estándar `django.contrib.auth.User`; no hay `AUTH_USER_MODEL` propio. La info de InterSoft vive en `Perfil` (usuario↔empresa↔rol, `cuentas/models.py`).
- **Tabla de permisos propia:** `Rol`, `Permiso`, `RolPermiso` (N:M). `Perfil.tiene_permiso(codigo)` resuelve vía `RolPermiso`.
- **Roles base** (3 del sistema, globales, protegidos contra borrado/renombrado): `ADMINISTRADOR`, `EMPLEADO`, `CLIENTE` (`cuentas/models.py` + `ROLES_DEL_SISTEMA` en `serializers_admin.py`). Se admiten **roles personalizados por empresa** (sección deuda).
- **Permisos finos** (`PERMISOS_BASE`, sembrados en `cuentas/migrations/0003`): `usuarios.gestionar`, `roles.asignar`, `productos.gestionar`, `inventario.movimientos`, `clientes.gestionar`, `ventas.gestionar`, `reportes.ver`, `configuracion.gestionar`. El módulo Empleados añade permisos tipo `empleado.*`.
- **Control de acceso (backend):** clases `BasePermission` en `cuentas/permissions.py`:
  - `EsAdministrador` (rol == ADMINISTRADOR, cuenta activa),
  - `EsPersonal` (ADMINISTRADOR o EMPLEADO),
  - `TienePermiso(codigo)` (factory por permiso fino, usado en Empleados).
  - Global: `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` (`settings.py`). Las vistas públicas/públicas-anónimas lo sobrescriben con `AllowAny` explícito (tienda, registro, login).
- **Extras de seguridad de cuenta:**
  - `CambioPasswordMiddleware` bloquea toda la API (403 `CAMBIO_PASSWORD_REQUERIDO`) si `Perfil.debe_cambiar_password=True`, salvo login/me/cambiar-password (`cuentas/middleware.py`).
  - Bloqueo por fuerza bruta (5 intentos / 15 min).
  - Tokens de recuperación con expiración (30 min).

### Roles: tenancy corregido (ver también sección 10)
- `Rol` ahora tiene FK `empresa` nullable (`cuentas/models.py:24`) y `UniqueConstraint(empresa, nombre)` (`models.py:34`). Los roles base son `empresa=None`; los personalizados pertenecen a su empresa.
- `roles_visibles(empresa)` (`views_admin.py:48`) consulta `Q(empresa=empresa) | Q(empresa__isnull=True)`: un ADMINISTRADOR solo ve sus roles + los del sistema, nunca los de otra empresa.
- `obtener_rol(empresa, id)` (`views_admin.py:241`) filtra por empresa en detalle/PUT/DELETE/clonar: operar sobre un rol ajeno devuelve 404.

---

## 4. Modelos de negocio

Todos heredan de `TimeStampedModel` (`core/models.py:8-24`): UUID PK + timestamps + `deleted_at` (soft delete) + `esta_activo`. Resumen (modelos en `core/models.py`):

| Modelo | Campos clave | Tenant |
|---|---|---|
| `Empresa` | nombre, nit (único), slug (único), plan, activa | el tenant |
| `Categoria` | nombre, descripcion | `empresa` FK |
| `Producto` | nombre, sku, precio, stock, stock_minimo, imagen, activo, `stock_bajo` | `empresa` FK; CHECK precio/stock ≥0; índice stock |
| `ComentarioProducto` | calificacion (1-5), comentario | por usuario+producto (marketplace) |
| `Favorito` | — | por usuario+producto |
| `Cliente` | nombre, tipo_documento, numero_documento, `DOCUMENTO_GENERICO` ("0000000000") + `generico()` | `empresa` FK nullable; `unique(empresa, tipo_doc, numero_doc)` |
| `Venta` | numero_factura (autogen), subtotal, descuento, total, estado, metodo_pago, motivo_anulacion | `empresa` FK; CHECK total/descuento ≥0; `unique(empresa, numero_factura)`; índice (empresa, estado, fecha) |
| `DetalleVenta` | cantidad, precio_unitario, `subtotal` | vía `venta.empresa`; CHECK cantidad>0 |
| `MovimientoInventario` | tipo (entrada/salida/ajuste), cantidad, motivo | vía `producto.empresa` |
| `Notificacion` | tipo (stock/factura/camara/sistema), estado (nueva/revisada/resuelta), canal (whatsapp/email/ninguno), entrega_pendiente, leida | `empresa` FK (multi-tenant) + `usuario` |
| `Cupon` | codigo, porcentaje, activo, fecha_inicio/fin, `esta_vigente` | `empresa` FK; unique(empresa, codigo) |
| `Carrito` / `CarritoItem` | 1 carrito por usuario; items por producto | por usuario (marketplace), `empresa` nullable |
| `FacturaElectronica` | numero (único), cufe, estado (pendiente/enviada/aprobada/rechazada/fallida), motivo_rechazo, pdf, xml, intentos | OneToOne a `Venta` |
| `NotaCredito` | numero (único), cufe_nota, estado, motivo, pdf, xml, reverso_stock | FK a `Venta.original` |
| `IAConversacion` / `IAMensaje` | título, estado; mensajes (rol/estado/error) | por usuario |
| `Camara` | nombre, ubicacion, url_stream, activa | `empresa` FK |

> A diferencia de la auditoría previa, **`Venta`, `DetalleVenta`, `MovimientoInventario` y `Notificacion` YA tienen API REST** (ver sección 5) y `FacturaElectronica`/`NotaCredito` son modelos nuevos de la fase DIAN.

---

## 5. URLs y views

Montaje raíz (`backend/intersoft/urls.py`): `admin/`, `api/auth/` (cuentas), `api/seguridad/` (cuentas_admin, solo ADMIN), y `api/` incluye los módulos de `core/`. Resumen de rutas **por módulo** (todas las vistas tienen lógica real; ninguna es placeholder):

| Módulo | Rutas (prefijo `/api/`) | Permisos |
|---|---|---|
| **Auth** (`cuentas/urls.py`) | `auth/login`, `auth/me`, `auth/cambiar-password`, `auth/registro`, `auth/registro/comprador`, `auth/email-disponible`, `auth/password-reset[/confirmar]`, `auth/refresh` | AllowAny (auth/registro), auth (me/cambiar-password) |
| **Seguridad** (`cuentas/urls_admin.py`) | `seguridad/usuarios[/<id>][/desactivar|reactivar]`, `seguridad/roles[/<id>][/clonar]`, `seguridad/permisos` | ADMIN |
| **Catálogo** (`core/urls_catalogo.py`) | `clientes[/<id>][/<accion>]`, `clientes/generico`, `productos[/<id>][/<accion>]`, `categorias` | EsPersonal |
| **Ventas/inventario/alertas** (`core/urls_ventas.py`) | `ventas`, `ventas/pos`, `ventas/<id>[/anular]`, `inventario`, `inventario/productos`, `inventario/<id>/ajustar`, `alertas`, `alertas/<id>/revisar`, `alertas/<id>/actualizar-stock` | EsPersonal |
| **Tienda/marketplace** (`core/urls_tienda.py`) | `tienda/<slug>/catalogo[/<id>]`, `tienda/catalogo[/<id>/comentarios]`, `tienda/cupones[/validar]`, `tienda/carrito[/items[/<id>]][/cupon]`, `tienda/checkout`, `tienda/completar-comprador`, `tienda/pedidos`, `tienda/favoritos[/<id>][/estado]` | Catálogo público/comentarios GET: AllowAny; carrito/favoritos/validar: auth; cupones (CRUD): EsPersonal |
| **Facturación DIAN** (`core/urls_facturacion.py`) | `facturacion[/<id>][/reenviar|reintentar]`, `notas-credito[/<id>]` | EsPersonal |
| **Dashboard** (`core/urls_dashboard.py`) | `dashboard/resumen`, `dashboard/ventas`, `dashboard/top-productos`, `dashboard/clientes-frecuentes`, `dashboard/inventario`, `dashboard/categorias` | ADMIN |
| **Reportes** (`core/urls_reportes.py`) | `reportes/tipos`, `reportes/vista`, `reportes/exportar` (excel/pdf) | ADMIN |
| **IA** (`core/urls_ia.py`) | `ia/conversaciones[/<id>]`, `ia/chat` | EsPersonal + rate-limit |
| **Monitoreo** (`core/urls_monitoreo.py`) | `camaras[/<id>][/grabacion]`, `notificaciones[/<id>]` | ADMIN |
| **Empleados** (`core/urls_empleados.py`) | `empleados[/<id>][/password][/<accion>]` | TienePermiso |

### Puntos notables de las views
- **Dashboard/Reportes se apoyan en vistas SQL** de MySQL (`core/migrations/0006_dashboard_vistas.py` + `core/analytics.py`) en vez de MongoDB; exportación CSV/PDF sin dependencias extra (`views_reportes.py`).
- **Tienda pública** (`views_tienda.py`): `CatalogoPublicoView`/`CatalogoProductoDetailView` son `AllowAny`, pero **scoped por `slug` de empresa** (o por empresa del usuario en variantes de compatibilidad). El `CuponValidarView` limita la validación de cupón a las **empresas presentes en el carrito del comprador** (`views_tienda.py:376-380`), evitando enumerar/leer cupones ajenos.
- **IA** (`views_ia.py` + `ia_engine.py`): proveedores `mock|groq|openai`; contexto de negocio cacheado por empresa (TTL 60s); **rate-limit por usuario** con ventana deslizante vía cache (`ia_engine.verificar_rate_limit`); conserva la conversación en error 502 para reintento sin duplicar.
- **Facturación DIAN** (`views_facturacion.py` + `core/services/dian_adapter.py`): flujo atómico (crear+enviar+revertir) con `select_for_update`; CUFE SHA-384; estados completa con reintento; OneToOne antifuga de factura por venta.
- **Concurrencia:** operaciones de dinero/stock (POS, anulación, ajuste, nota crédito, checkout) usan `transaction.atomic()` + `select_for_update`; correlativo de `numero_factura` serializado bloqueando la fila de empresa. Cubierto por `tests_fase5.py` (carreras) y `tests_integridad.py`.
- **Errores uniformes:** manejador global (`core/exceptions.py`) que devuelve `{codigo, detalle, errores}` sin tracebacks ni datos sensibles.
- **Auditoría de actividad:** `AuditoriaMiddleware` (`cuentas/middleware.py`) registra toda escritura autenticada exitosa en `ActividadUsuario`.

---

## 6. Plantillas

- El backend es **API REST pura**; las únicas plantillas son 4 de error (`backend/templates/400|403|404|500.html`). No hay `base.html` ni `{% extends %}`/`{% include %}`; cada una es HTML autocontenido con su CSS inline (candidato persistente a refactor, deuda menor).
- No existe `static/` propio del proyecto (solo `staticfiles/` para `collectstatic`) y **no se usa Tailwind** en el backend. Todo el CSS/HTML de la interfaz vive en el frontend Angular.

---

## 7. Tests

- **Backend (Django test runner, 296 tests):**
  - `core/tests.py` — 137
  - `core/tests_fase5.py` — 35 (solidez, errores, concurrencia)
  - `core/tests_aislamiento.py` — 28 (multi-tenancy con 2 empresas)
  - `core/tests_dian.py` — 19 (CUFE, PDF/XML, estados)
  - `core/tests_empleados.py` — 12
  - `core/tests_integridad.py` — 5
  - `cuentas/tests.py` — 60
- **Frontend:** 7 archivos `*.spec.ts` (guards, auth.service, etc.) vía Vitest con cobertura v8.
- **Comando correcto:** `python manage.py test` desde `backend/` (el `tests/README.md` ya **no** menciona pytest; está corregido). El runner de CI ejecuta `check`, `makemigrations --check --dry-run`, `migrate`, la suite completa y, en dev, `ruff` + `bandit` + `coverage --fail-under=70`.
- **CI** (`.github/workflows/ci.yml`): jobs frontend (npm ci → lint → build → tests → **npm audit**) y backend (Python 3.12 + MySQL 8 servicio, con `DEBUG=False` ejerciendo las protecciones de producción, fail-fast si falta `SECRET_KEY`/`ALLOWED_HOSTS=*`).

---

## 8. Ortografía / texto de interfaz

Nota metodológica (idéntica a la anterior): buena parte de las coincidencias son identificadores de código (`codigo:`, `descripcion:`, `telefono:`) y no texto legible. Sin embargo, persisten casos de **texto visible sin tildes** en el panel interno, p. ej.:
- `dashboard`/`configuracion`: "Desde aqui administraras…", "Mas opciones de configuracion disponibles proximamente."
- Formularios: `<label>` "Telefono", "Descripcion", "Minimo 8 caracteres…".
- Tienda/panel: varios placeholders y textos sin acentos.

Se **documenta, no se corrige** (auditoría de solo lectura). Recomendación: pasar una pasada de acentuación sobre los textos de plantillas HTML de `frontend/src/app/features` (especialmente etiquetas, ayudas y estados vacíos).

---

## 9. Deuda técnica y riesgos VIGENTES

> Los riesgos críticos de la auditoría previa fueron resueltos (sección 10). Lo que sigue es deuda/menos riesgos conocidos, ninguno es un bug crítico abierto que bloquee la entrega (coherente con `docs/RIESGOS.md`).

### Backend
1. **Firma DIAN real (producción):** el adaptador está implementado (`DIAN_MOCK=False` + SOAP via zeep) pero es **solo verificable con habilitación oficial**: falta el certificado PKCS12 y la firma **XAdES-EPES**; el CUFE y la transmisión asíncrona ("EN PROCESO") deben ajustarse al esquema vigente (`services/dian_adapter.py` docstring; `docs/ROADMAP.md` D1). Con `DIAN_MOCK=True` (default) se simula localmente.
2. **Correo/WhatsApp**: por defecto `EMAIL_BACKEND` = consola (desarrollo) o requiere SMTP (prod); WhatsApp solo si `WA_VINCULADO=True`. No hay envío real configurado en ningún entorno del repo (correcto para demo, pendiente para producción).
3. **`Notificacion` entrega y canales**: la entrega efectiva (email/WhatsApp) depende del `notificador.py` y de reintento manual (`reintentar_notificaciones`); verificar cobertura de reintentos en producción.
4. **Gestión de inventario en tienda pública**: el catálogo expone stock/precio; confirmar que no filtre datos de costos internos por rol (revisar serializador público).

### Frontend
5. **`lint` (Prettier) cubre solo 4 archivos** de los ~134 de `src/`: ajustado solo a `vitest-base.config.ts`, `test-setup.ts`, `configuracion.component.ts` y `tienda/catalogo/catalogo.component.ts` (`package.json` "lint"). El resto del código TS/HTML no pasa por formateo/chequeo de estilo en CI. Recomendación: lanzar Prettier sobre todo `src/`.
6. **Dependencias `^`/`~`** en `package.json` (a diferencia del backend que son `==`); reproducibilidad se apoya solo en el lockfile.
7. **Cobertura de tests del frontend limitada** (7 specs) frente a la complejidad (20+ features). El backend sí tiene gate de cobertura.

### Ambos
8. **`AUDITORIA.md` histórica** era el único registro del hallazgo de tenancy de roles; ya resuelto y cubierto por tests (sección 10).
9. **Plantillas de error duplicadas** (4 archivos HTML autocontenidos con CSS repetido) — refactor a `base.html` recomendado.

---

## 10. Resumen de la auditoría previa → estado actual

Los hallazgos críticos de la auditoría del 2026-08-25 **ya están corregidos**:

| Hallazgo previo (#) | Estado actual |
|---|---|
| 9.1 — **Fuga multi-tenant por `Rol` global** (roles sin empresa; cualquier ADMIN ve/edita/clona roles de otras empresas) | **CORREGIDO.** `Rol.empresa` FK nullable (`cuentas/models.py:24`), `UniqueConstraint(empresa, nombre)`, `roles_visibles()` y `obtener_rol(empresa, id)` filtran por tenant (`views_admin.py:48, 241`). Cubierto por `core/tests_aislamiento.py` (2 empresas). |
| 9.2 — Footer hardcodeado (teléfono, correo, redes de ejemplo) | **CORREGIDO.** `site-footer.component.ts` retiró datos de ejemplo (comentario en el propio archivo). Queda `DEFAULT_FROM_EMAIL` (ahora configurable vía `.env`). |
| 9.4 — `signals.py` usaba `print()` | **CORREGIDO.** `core/signals.py` usa `logging` (`logger.warning`). |
| 9.4 — `tests/README.md` decía "usa pytest" | **CORREGIDO.** Ahora indica `python manage.py test`. |
| 5 — Rutas de `core` sin `name=` | Persistente (deuda menor); sin impacto funcional. |
| 4 — `Venta`/`DetalleVenta`/`MovimientoInventario`/`Notificacion` sin API | **RESUELTO.** Tienen vistas y rutas (ventas POS, inventario, alertas, monitoreo). |

**Novedades desde la auditoría previa (no cubiertas antes):** módulo Empleados, marketplace/tienda (carrito, cupones, favoritos, checkout, pedidos), facturación DIAN real (PDF/XML/CUFE/notas crédito), dashboard+reportes con vistas SQL, asistente IA, monitoreo (cámaras+notificaciones), Docker+compose, CI endurecido (ruff/bandit/coverage/npm audit), design system (`docs/DESIGN_SYSTEM.md`) y roadmap (`docs/ROADMAP.md`).

---

## Conclusión

Proyecto **sólido y maduro**, con buenas prácticas de seguridad (fail-fast en producción, locks de concurrencia, aislamiento multi-tenant verificado por tests), API uniforme y documentación completa. El único hallazgo crítico histórico (fuga por roles) fue resuelto y probado. La deuda vigente es de **mejora/deriva de producto** (producción DIAN con habilitación real, cobertura del frontend/lint, acentuación de textos), no bugs abiertos que bloqueen la entrega. Ver `docs/RIESGOS.md` y `docs/ROADMAP.md` para el detalle priorizado.

### Preguntas para Daniel
1. ¿El módulo **Empleados** (permisos finos `empleado.*`) debe reemplazar/aunar el CRUD de `/api/seguridad/usuarios/` de la fase 2, o se mantienen ambos en paralelo deliberadamente?
2. ¿Se dispone (o es inminente) de la **habilitación DIAN** y el certificado PKCS12 para validar el firmado XAdES-EPES y el CUFE oficial, o `DIAN_MOCK=True` queda como entrega hasta entonces?
3. ¿Ampliamos el **`lint` de Prettier a todo `src/`** y la cobertura de tests del frontend (que hoy es mucha más baja que la del backend)?
4. ¿Corremos una pasada de **acentuación** sobre los textos visibles del panel interno (etiquetas, ayudas, estados vacíos)?
