# AUDITORÍA DEL PROYECTO — InterSoft (solo lectura)

Fecha: 2026-08-25. Rama: `Mark2-actualizado`. Alcance: `backend/` (Django). No se modificó, creó ni borró ningún archivo salvo este reporte.

**Nota sobre `SPEC.md`:** el enunciado indica "léelo para saber qué información te interesa". Se buscó en la raíz del repositorio y **NO EXISTE** (`ls SPEC.md` → *No such file or directory*). No se pudo usar como guía; esta auditoría cubre exactamente los 9 puntos solicitados en el mensaje.

**Aviso importante antes de empezar:** varias preguntas del enunciado (plantillas base, dashboard, `static/`, Tailwind) están formuladas como si este fuera un proyecto Django monolítico con render server-side. **No lo es.** El backend (`backend/`) es una API REST pura (Django REST Framework + JWT) sin views que rendericen HTML de negocio; el dashboard y toda la interfaz visual viven en `frontend/` (Angular 22, SPA aparte). Esto se documenta con evidencia en cada sección correspondiente en vez de asumirse.

---

## 1. Stack y configuración

- **Django:** rango declarado `Django>=5.2,<6.0` (`backend/requirements.txt:1`). Versión instalada en el entorno donde se ejecutó esta auditoría: `5.2.17` (verificado con `python -c "import django; print(django.VERSION)"`).
- **Python:** no hay `runtime.txt`, `.python-version` ni `pyproject.toml` en `backend/` ni en la raíz — **NO ENCONTRADO** ningún pin explícito de versión de Python en el repositorio. La versión del intérprete usado en esta máquina es `3.14.6` (`python --version`), pero eso es el entorno local, no una declaración del proyecto.
- **Dependencias** (`backend/requirements.txt`, líneas 1-11):
  - `djangorestframework>=3.16` (línea 2)
  - `djangorestframework-simplejwt>=5.3` (línea 3)
  - `django-cors-headers>=4.4` (línea 4)
  - `python-decouple>=3.8` (línea 5)
  - `Pillow>=11.0.0` (línea 6)
  - `mysqlclient>=2.2` (línea 7)
  - `PyMySQL>=1.1` (línea 11) — alternativa pura en Python, activada automáticamente si `mysqlclient` no compila (comentario en líneas 9-10).
- **`pyproject.toml`:** NO EXISTE en `backend/` ni en la raíz.
- **Tailwind / build de CSS:** NO EXISTE en el backend. Búsqueda `find . -iname "*tailwind*"` (excluyendo `venv/` y `node_modules/`) → sin resultados.
- **CSS plano:** no hay ninguna carpeta `static/` propia del proyecto (`find . -type d -iname "static"` sólo devuelve rutas dentro de `backend/venv/Lib/site-packages/...`, es decir, CSS de terceros — el admin de Django y el navegador de DRF — no del proyecto). El único CSS del proyecto son bloques `<style>` inline dentro de las 4 plantillas de error: `backend/templates/400.html:7-29`, `403.html`, `404.html:7-29`, `500.html:7-30`.
- **Librería de iconos instalada:** NO ENCONTRADO ningún paquete de iconos (Font Awesome, Bootstrap Icons, Heroicons, Feather, Lucide) referenciado en código propio del backend. El único `font-awesome-4.0.3.css` que aparece en el repo es interno de `djangorestframework` (`backend/venv/Lib/site-packages/rest_framework/static/rest_framework/css/font-awesome-4.0.3.css`), parte del navegador de la API, no del proyecto.
- **Static files config** (`backend/intersoft/settings.py`):
  - `STATIC_URL = 'static/'` — línea 94
  - `STATIC_ROOT = BASE_DIR / 'staticfiles'` — línea 95
  - `MEDIA_URL = '/media/'` — línea 96
  - `MEDIA_ROOT = BASE_DIR / 'media'` — línea 97
  - Servidas en desarrollo vía `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` cuando `DEBUG=True` — `backend/intersoft/urls.py:13-14`.
- **`charset` y `lang` en plantillas:** las 4 plantillas de `backend/templates/` declaran `<html lang="es">` y `<meta charset="UTF-8">` (ejemplo exacto: `backend/templates/404.html:2` y `:4`; mismo patrón confirmado en `400.html`, `403.html`, `500.html`). `LANGUAGE_CODE = 'es-co'` y `TIME_ZONE = 'America/Bogota'` están declarados en `backend/intersoft/settings.py:89-90`.

---

## 2. Multi-tenancy

- **Mecanismo:** NO hay `django-tenants`, NO hay separación por *schema* de PostgreSQL, NO hay resolución por subdominio. `INSTALLED_APPS` (`backend/intersoft/settings.py:25-37`) no incluye ningún paquete de tenancy. Es **tenancy por Foreign Key**: todo modelo de negocio cuelga de `Empresa` mediante `empresa = models.ForeignKey(Empresa, ...)` — declarado explícitamente en `backend/core/models.py` para `Categoria:46`, `Producto:59`, `Cliente:97`, `Venta:131`.
- **Modelo del tenant:** `Empresa`, definido en `backend/core/models.py:27-42`. Campos relevantes: `nombre` (línea 30), `nit` — único, línea 31 (`unique=True`), `email` único (línea 32), `telefono`, `direccion`, `plan` con choices `basic/pro/enterprise` (línea 28-29, 35), `activa` (línea 36). Hereda de `TimeStampedModel` (UUID como PK, `created_at`, `updated_at`, `deleted_at` — `backend/core/models.py:8-24`).
- **Dónde se resuelve el tenant de la request:** NO hay middleware de resolución de tenant. Se resuelve implícitamente en cada vista, leyendo `request.user.perfil.empresa` — el `Perfil` (join entre `auth_user` y `Empresa`, `backend/cuentas/models.py:63-113`) es lo que ata cada usuario autenticado a su empresa. Ejemplos citados: `backend/core/views_catalogo.py:39, 52, 70, 91, 121, 134, 158, 179, 244, 251, 254`; `backend/cuentas/views_admin.py:41, 58, 71, 122, 146`.
- **¿Filtrado automático (manager) o manual por view?** **Manual, por vista.** No existe ningún `Manager`/`QuerySet` personalizado en `backend/core/models.py` ni en `backend/cuentas/models.py` que filtre por empresa automáticamente (verificado leyendo el archivo completo: no hay `objects = ...Manager()` en ningún modelo). Cada `APIView` en `backend/core/views_catalogo.py` filtra a mano con `.filter(empresa=request.user.perfil.empresa, ...)` — ver citas del punto anterior.
- **Excepción encontrada — `Rol` es GLOBAL, no por tenant.** El modelo `Rol` (`backend/cuentas/models.py:11-30`) **no tiene campo `empresa`**; su único campo de identidad es `nombre = models.CharField(max_length=30, unique=True)` (línea 16, único a nivel de toda la base de datos, no por empresa). Consecuencia verificada en código (detalle completo en la sección 9): las vistas de gestión de roles (`RolesSeguridadView.get`, `backend/cuentas/views_admin.py:175-178`; `RolDetalleView.obtener_rol`, línea 201-202; `RolClonarView.post`, líneas 277-299) consultan `Rol.objects...` **sin ningún filtro por `empresa`**. Esto es el hallazgo de riesgo más importante de esta auditoría — ver sección 9.

---

## 3. Usuarios y RBAC

- **Modelo de usuario:** NO es un modelo `AUTH_USER_MODEL` personalizado. `settings.py` no define `AUTH_USER_MODEL` (grep sin resultados), por lo que se usa el `django.contrib.auth.models.User` estándar de Django (`AbstractUser` sin extender). La info específica de InterSoft (empresa, rol, bloqueo de intentos) vive en un modelo aparte, `Perfil`, ligado 1 a 1: `usuario = models.OneToOneField(settings.AUTH_USER_MODEL, ...)` — `backend/cuentas/models.py:68-69`.
- **Cómo se determina el rol:** ni grupos de Django (`django.contrib.auth.models.Group` no se usa en ningún `.py` del proyecto — sin resultados al buscar `Group` fuera de `venv/`) ni un campo plano de texto. Es una **tabla de permisos propia**: `Rol` (`backend/cuentas/models.py:11-30`), `Permiso` (líneas 33-45) y `RolPermiso` como tabla intermedia N:M (líneas 48-60). `Perfil.rol` es una FK a `Rol` (línea 71) y `Perfil.tiene_permiso(codigo)` (líneas 88-89) resuelve el permiso vía `RolPermiso.objects.filter(rol=self.rol, permiso__codigo=codigo).exists()`.
- **Roles que existen hoy (nombre EXACTO en código):**
  - `"ADMINISTRADOR"` — `backend/cuentas/models.py:64`, sembrado en `backend/cuentas/management/commands/seed_roles.py:20`.
  - `"EMPLEADO"` — `backend/cuentas/models.py:64`, sembrado en `seed_roles.py:21-22`.
  - `"CLIENTE"` — `backend/cuentas/models.py:65`, sembrado en `seed_roles.py:23`.
  - Son los únicos 3 declarados como constante `ROLES` en el modelo `Perfil` (`backend/cuentas/models.py:64-65`) y como `ROLES_DEL_SISTEMA = {"ADMINISTRADOR", "EMPLEADO", "CLIENTE"}` en `backend/cuentas/serializers_admin.py:13`. **Además de estos 3, el sistema permite crear roles adicionales arbitrarios** vía `POST /api/seguridad/roles/` (`RolesSeguridadView.post`, `backend/cuentas/views_admin.py:180-193`) — no hay lista cerrada de roles en tiempo de ejecución, sólo estos 3 están protegidos contra borrado/renombrado (`ROLES_DEL_SISTEMA`, ver `backend/cuentas/views_admin.py:227-231, 251-254`).
- **Lista de permisos definidos** (`PERMISOS_BASE`, `backend/cuentas/management/commands/seed_roles.py:6-15`, sembrados también en la migración `backend/cuentas/migrations/0003_seed_rbac.py:11-18`):
  1. `usuarios.gestionar`
  2. `roles.asignar`
  3. `productos.gestionar`
  4. `inventario.movimientos`
  5. `clientes.gestionar`
  6. `ventas.gestionar`
  7. `reportes.ver`
  8. `configuracion.gestionar`
  - Asignación por rol (`PERMISOS_POR_ROL`, `seed_roles.py:19-24`): **ADMINISTRADOR** recibe los 8; **EMPLEADO** recibe 5 (`productos.gestionar`, `inventario.movimientos`, `clientes.gestionar`, `ventas.gestionar`, `reportes.ver`); **CLIENTE** recibe 0 (comentario explícito: "su portal se construye en fases posteriores", línea 17-18).
- **Decoradores/mixins de permisos usados:** son clases `BasePermission` de DRF, no decoradores de función-vista clásicos de Django. Definidas en `backend/cuentas/permissions.py`:
  - `EsAdministrador` (líneas 9-14) — exige `perfil.rol.nombre == "ADMINISTRADOR"`. Se usa en las 8 vistas de `backend/cuentas/views_admin.py` (fase 2): líneas 38, 68, 119, 143, 173, 198, 275, 304.
  - `EsPersonal` (líneas 17-27) — exige rol en `{"ADMINISTRADOR", "EMPLEADO"}`. Se usa en las 6 vistas de `backend/core/views_catalogo.py` (fase 3): líneas 36, 67, 117, 153, 214, 241.
  - Ambas se combinan siempre con `IsAuthenticated` de DRF (ej. `permission_classes = [IsAuthenticated, EsAdministrador]`, `backend/cuentas/views_admin.py:38`).
  - Configuración global: `DEFAULT_PERMISSION_CLASSES = ('rest_framework.permissions.IsAuthenticated',)` — `backend/intersoft/settings.py:105-107`. Las vistas de `backend/cuentas/views.py` (login, registro, recuperación) sobreescriben esto con `permission_classes = [AllowAny]` explícitamente (líneas 21, 79, 93, 105, 129).

---

## 4. Modelos de negocio

Todos en `backend/core/models.py`, heredando de `TimeStampedModel` (UUID PK + `created_at`/`updated_at`/`deleted_at` + `soft_delete()` — líneas 8-24):

| Modelo | Líneas | Campos clave | Relación con el tenant |
|---|---|---|---|
| `Empresa` | 27-42 | `nombre`, `nit` (único), `email` (único), `plan` (choices), `activa` | Es el tenant mismo |
| `Categoria` | 45-55 | `nombre`, `descripcion` | `empresa` FK (línea 46), único `(empresa, nombre)` (línea 51) |
| `Producto` | 58-91 | `nombre`, `sku`, `precio` (Decimal), `stock`, `stock_minimo`, `imagen`, `activo`, propiedad `stock_bajo` (líneas 89-91) | `empresa` FK (línea 59), único `(empresa, sku)` (línea 72). Constraints CHECK en BD: `precio>=0`, `stock>=0`, `stock_minimo>=0` (líneas 76-84) |
| `Cliente` | 94-122 | `nombre`, `tipo_documento` (CC/NIT/CE/PAS), `numero_documento`, `usuario` (OneToOne opcional a `auth_user`), propiedad `total_compras` (líneas 117-122) | `empresa` FK (línea 97), único `(empresa, tipo_documento, numero_documento)` (línea 111) |
| `Venta` | 125-162 | `numero_factura` (autogenerado, líneas 153-157), `total`, `estado` (pendiente/completada/anulada), `metodo_pago`, `cliente` FK, `vendedor` FK a `auth_user` | `empresa` FK (línea 131). Constraint CHECK `total>=0` (línea 146-147) |
| `DetalleVenta` | 165-187 | `venta` FK, `producto` FK, `cantidad`, `precio_unitario`, propiedad `subtotal` (185-187) | Vía `venta.empresa` (no tiene FK directa a `Empresa`). Único `(venta, producto)` (línea 174) |
| `MovimientoInventario` | 190-209 | `producto` FK, `usuario` FK, `tipo` (entrada/salida/ajuste), `cantidad`, `motivo` | Vía `producto.empresa` (no tiene FK directa a `Empresa`) |
| `Notificacion` | 212-224 | `usuario` FK (nullable), `mensaje`, `leida` | Vía `usuario` → no tiene FK a `Empresa` ni a `Cliente` |

**"Factura" como modelo separado: NO EXISTE.** La factura es el propio modelo `Venta`: su campo `numero_factura` se autogenera en `_generar_numero_factura()` (`backend/core/models.py:153-157`) con el formato `{8 primeros chars del UUID de empresa en mayúsculas}-{fecha}-{consecutivo de 5 dígitos}`.

**Importante — estos modelos NO tienen API expuesta.** `Venta`, `DetalleVenta`, `MovimientoInventario` y `Notificacion` sólo aparecen en `backend/core/models.py`, `backend/core/admin.py` (líneas 44-51, 54-57, 60-66, 69-74 respectivamente — sólo Django Admin) y en `backend/core/tests.py` (se crean directo con el ORM para probar restricciones de modelo). Búsqueda `grep -rn "MovimientoInventario\|Notificacion" backend/core/urls_catalogo.py backend/core/views_catalogo.py backend/core/serializers_catalogo.py` → **sin resultados**. No hay ningún serializer, vista ni ruta para estos 3 modelos, ni para crear/listar ventas. Solo `Cliente`, `Producto` y `Categoria` tienen CRUD vía API (sección 5).

---

## 5. URLs y views

### Tabla de rutas

Montaje raíz en `backend/intersoft/urls.py:6-11`:

| Prefijo | Incluye | Línea |
|---|---|---|
| `admin/` | `admin.site.urls` (Django Admin) | 7 |
| `api/auth/` | `cuentas.urls` | 8 |
| `api/seguridad/` | `cuentas.urls_admin` (comentario: "fase 2: solo ADMINISTRADOR") | 9 |
| `api/` | `core.urls_catalogo` (comentario: "fase 3: clientes y productos") | 10 |

**`backend/cuentas/urls.py`** (todas con `name=`):

| Ruta completa | `name` | View | Línea |
|---|---|---|---|
| `POST /api/auth/login/` | `auth-login` | `LoginView` | urls.py:8 |
| `POST /api/auth/registro/` | `auth-registro` | `RegistroEmpresaView` | urls.py:9 |
| `GET /api/auth/email-disponible/` | `auth-email-disponible` | `EmailDisponibleView` | urls.py:10 |
| `POST /api/auth/password-reset/` | `auth-password-reset` | `SolicitarRecuperacionView` | urls.py:11 |
| `POST /api/auth/password-reset/confirmar/` | `auth-password-reset-confirmar` | `ConfirmarRecuperacionView` | urls.py:12 |

**`backend/cuentas/urls_admin.py`** (todas con `name=`):

| Ruta completa | `name` | View | Línea |
|---|---|---|---|
| `GET/POST /api/seguridad/usuarios/` | `seguridad-usuarios` | `UsuariosSeguridadView` | urls_admin.py:14 |
| `GET/PUT/PATCH /api/seguridad/usuarios/<uuid:id>/` | `seguridad-usuario-detalle` | `UsuarioSeguridadDetalleView` | urls_admin.py:15 |
| `POST /api/seguridad/usuarios/<uuid:id>/desactivar/` | `seguridad-usuario-desactivar` | `UsuarioDesactivarView` | urls_admin.py:16 |
| `POST /api/seguridad/usuarios/<uuid:id>/reactivar/` | `seguridad-usuario-reactivar` | `UsuarioReactivarView` | urls_admin.py:17 |
| `GET/POST /api/seguridad/roles/` | `seguridad-roles` | `RolesSeguridadView` | urls_admin.py:20 |
| `GET/PUT/PATCH/DELETE /api/seguridad/roles/<uuid:id>/` | `seguridad-rol-detalle` | `RolDetalleView` | urls_admin.py:21 |
| `POST /api/seguridad/roles/<uuid:id>/clonar/` | `seguridad-rol-clonar` | `RolClonarView` | urls_admin.py:22 |
| `GET /api/seguridad/permisos/` | `seguridad-permisos` | `PermisosCatalogoView` | urls_admin.py:25 |

**`backend/core/urls_catalogo.py`** — **ninguna ruta tiene `name=`** (verificado leyendo el archivo completo: ningún `path()` recibe el argumento `name`):

| Ruta completa | View | Línea |
|---|---|---|
| `GET/POST /api/clientes/` | `ClientesView` | urls_catalogo.py:9 |
| `GET/PUT/PATCH/DELETE /api/clientes/<uuid:id>/` | `ClienteDetalleView` | urls_catalogo.py:10 |
| `GET/POST /api/productos/` | `ProductosView` | urls_catalogo.py:12 |
| `GET/PUT/PATCH/DELETE /api/productos/<uuid:id>/` | `ProductoDetalleView` | urls_catalogo.py:13-14 |
| `POST /api/productos/<uuid:id>/<str:accion>/` | `ProductoEstadoView` (`accion` = `desactivar` o `reactivar`) | urls_catalogo.py:15-16 |
| `GET/POST /api/categorias/` | `CategoriasView` | urls_catalogo.py:18 |

### La view del dashboard actual

**NO EXISTE ninguna view de dashboard en este backend Django.** `backend/core/views.py` está vacío salvo el boilerplate generado por `startapp` (`from django.shortcuts import render` — sin ninguna función/clase definida, archivo completo de 3 líneas). Búsqueda `grep -rni "dashboard" backend --include="*.py"` → **sin resultados** en ningún archivo `.py` del backend. El "dashboard" que sí existe está en el frontend Angular, como componente `DashboardComponent` (`frontend/src/app/features/dashboard/dashboard.component.ts`), fuera del alcance de esta auditoría (que es sólo del backend Django, como pediste). Ese componente no consume ningún endpoint del backend: su contenido es un arreglo estático de 3 "módulos" marcados `Próximamente`.

### Rutas implementadas vs. placeholder

- **Implementadas de verdad** (tienen view, serializer, tests que pasan): las 5 de `cuentas/urls.py`, las 8 de `cuentas/urls_admin.py`, y las 6 de `core/urls_catalogo.py`. Total: **19 rutas de API**, todas con lógica real (no hay ningún `pass` ni `NotImplementedError` en las vistas).
- **Placeholder / no existentes:** no hay rutas declaradas-pero-vacías en el sentido de "URL registrada que apunta a una vista sin implementar". El "placeholder" real es la ausencia total de rutas para `Venta`, `DetalleVenta`, `MovimientoInventario` y `Notificacion` (sección 4) y la ausencia de cualquier endpoint de dashboard/reportes (no hay ruta que empiece por `/api/dashboard` ni `/api/reportes` — grep sin resultados).

---

## 6. Plantillas

Árbol completo de `backend/templates/` (única carpeta de templates del proyecto — `TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']`, `backend/intersoft/settings.py:56`):

```
backend/templates/
├── 400.html
├── 403.html
├── 404.html
├── 500.html
└── README.md
```

- **`base.html`: NO EXISTE.** Búsqueda `find backend -iname "base.html"` (excluyendo `venv/`) → sin resultados.
- **Quién hereda de él:** nadie — no hay ningún `{% extends %}` en ninguna de las 4 plantillas (son documentos HTML completos y autocontenidos, cada uno con su propio `<!DOCTYPE html>`, `<head>` y `<style>`).
- **Componentes/includes reutilizables:** NO EXISTEN. Búsqueda de `{% include %}` en `backend/templates/*.html` → sin resultados.
- **HTML duplicado entre plantillas: SÍ, confirmado.** Las 4 plantillas (`400.html`, `403.html`, `404.html`, `500.html`) repiten, cada una por separado, el mismo bloque de CSS inline para `.tarjeta` (tarjeta blanca centrada, sombra, borde) y `.marca` (logo "InterSoft" al pie). Comparación línea a línea entre `404.html:14-18` y `500.html:14-18`: el selector `.tarjeta { max-width: 460px; ... }` es carácter por carácter idéntico en ambos archivos. Lo mismo ocurre con el bloque `.marca` (`404.html:27-28` vs `500.html:28-29`, idéntico). Esto es un candidato directo a extraer a un único `base.html` con `{% block %}`, algo que hoy no existe.
- **`templates/README.md`** (`backend/templates/README.md:1-3`): una sola línea de descripción genérica ("Plantillas HTML utilizadas por el backend"), sin instrucciones adicionales.

---

## 7. Tests

- **¿Existen?** Sí. Dos archivos: `backend/core/tests.py` (377 líneas, **38** métodos `test_*`, repartidos en 14 clases — `BaseCoreTest`, `ValidacionesGlobalesTest`, `ClienteDocumentoUnicoTest`, `DetalleVentaTest`, `MovimientoInventarioTest`, `NotificacionTest`, `BorradoLogicoTest`, `VentaFacturaTest`, `BaseCatalogoTest`, `AccesoCatalogoTest`, `CrudClientesApiTest`, `CrudProductosApiTest`, `CategoriasApiTest`, `AuditoriaCatalogoTest`) y `backend/cuentas/tests.py` (440 líneas, **45** métodos `test_*`, en 11 clases — `BaseCuentasTest`, `RolesYPermisosTest`, `LoginTest`, `BloqueoPorIntentosTest`, `RecuperacionPasswordTest`, `AuditoriaTest`, `EmailUnicoTest`, `BaseSeguridadTest`, `AccesoSeguridadTest`, `CrudUsuariosTest`, `CrudRolesTest`). Total: **83 tests**.
- **Con qué comando corren — discrepancia encontrada:** `backend/tests/README.md:5` dice literalmente *"Usa `pytest` para ejecutar las pruebas."* Esto es **incorrecto/desactualizado**: se verificó que `pytest` **NO está instalado** (`python -c "import pytest"` → `ModuleNotFoundError: No module named 'pytest'`), tampoco `pytest-django`, y no existe `pytest.ini`, `conftest.py` ni `setup.cfg` en ningún lugar del repo. El comando que realmente funciona es el estándar de Django: `python manage.py test` (ejecutado desde `backend/`).
- **¿Pasan todos ahora mismo?** Sí. Salida cruda de `python manage.py test` (ejecutado el 2026-08-25 desde `backend/`, base de datos MySQL local disponible):

```
Creating test database for alias 'default'...
...................................................................................
----------------------------------------------------------------------
Ran 83 tests in 8.340s

OK
Destroying test database for alias 'default'...
```
(Las líneas `[ALERTA STOCK] ...` y `Roles listos: ...` que aparecen en la consola son `print()` del signal `backend/core/signals.py:9-13` y del comando `seed_roles.py:41-43`, disparados como efecto secundario de los propios tests — no son fallos ni advertencias del test runner.)

---

## 8. Ortografía

**Comando exacto solicitado**, ejecutado desde la raíz del repositorio:

```
$ grep -rInE "\b(aqui|administraras|minimos|facturacion|gestion|proximamente|siguenos|configuracion|numero|codigo|articulo|telefono|direccion|periodo|analisis|estadistica|informacion|descripcion|categoria|ultimo|dia|mas)\b" templates/ static/ --include="*.html" --include="*.js" --include="*.css"

grep: templates/: No such file or directory
grep: static/: No such file or directory
```

**Motivo:** ni `templates/` ni `static/` existen en la raíz del repositorio — son rutas del enunciado que no corresponden a la estructura real. Las plantillas HTML reales del backend están en `backend/templates/` (sección 6); no hay ningún `static/` propio del proyecto (sección 1); y el HTML/CSS/JS de la interfaz de usuario vive en `frontend/src/` (Angular, no archivos `.html`/`.css`/`.js` sueltos servidos por Django).

**Salida cruda adaptada a las rutas reales** (`backend/templates/` + `frontend/src/`, incluyendo también `.ts` ya que Angular no tiene `.js` fuente propio), mismo patrón, sin corregir nada:

```
backend/templates/400.html:19:  .codigo {
backend/templates/400.html:33:    <div class="codigo">400</div>
backend/templates/404.html:19:  .codigo {
backend/templates/404.html:33:    <div class="codigo">404</div>
frontend/src/app/app.routes.ts:45:    path: 'configuracion',
frontend/src/app/app.routes.ts:49:      import('./features/configuracion/configuracion.component').then((m) => m.ConfiguracionComponent),
frontend/src/app/core/models/auth.model.ts:36:  codigo: CodigoErrorAuth;
frontend/src/app/core/models/catalogo.model.ts:9:  telefono: string;
frontend/src/app/core/models/catalogo.model.ts:10:  direccion: string;
frontend/src/app/core/models/catalogo.model.ts:27:  descripcion: string;
frontend/src/app/core/models/catalogo.model.ts:41:  descripcion: string;
frontend/src/app/core/models/catalogo.model.ts:52:  descripcion: string;
frontend/src/app/core/models/catalogo.model.ts:57:  codigo?: string;
frontend/src/app/core/models/seguridad.model.ts:21:  codigo: string;
frontend/src/app/core/models/seguridad.model.ts:22:  descripcion: string;
frontend/src/app/core/models/seguridad.model.ts:28:  descripcion: string;
frontend/src/app/core/models/seguridad.model.ts:36:  descripcion: string;
frontend/src/app/core/models/seguridad.model.ts:41:  codigo?: string;
frontend/src/app/core/services/auth.service.ts:79:    if (e.status === 0) return { codigo: 'SIN_CONEXION', mensaje: 'No hay conexion con el servidor.' };
frontend/src/app/core/services/auth.service.ts:82:        codigo: 'CREDENCIALES_INVALIDAS',
frontend/src/app/core/services/auth.service.ts:86:    if (e.status === 403) return { codigo: 'USUARIO_INACTIVO', mensaje: 'Esta cuenta esta desactivada.' };
frontend/src/app/core/services/auth.service.ts:89:        codigo: 'CUENTA_BLOQUEADA',
frontend/src/app/core/services/auth.service.ts:93:    if (e.status === 400) return { codigo: 'DATOS_INVALIDOS', mensaje: cuerpo.detalle ?? 'Datos invalidos.' };
frontend/src/app/core/services/auth.service.ts:94:    return { codigo: 'ERROR_SERVIDOR', mensaje: 'El servidor tuvo un problema.' };
frontend/src/app/core/services/catalogo.service.ts:94:    return { codigo: cuerpo.codigo, detalle: mensaje };
frontend/src/app/core/services/catalogo.service.ts:96:  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
frontend/src/app/core/services/seguridad.service.ts:84:  if (cuerpo.codigo === 'ROL_CON_USUARIOS_ACTIVOS') return cuerpo;
frontend/src/app/core/services/seguridad.service.ts:88:    return { codigo: cuerpo.codigo, detalle: mensaje };
frontend/src/app/core/services/seguridad.service.ts:90:  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
frontend/src/app/core/validators/password.validators.ts:10:  if (!/[0-9]/.test(valor)) faltantes.push('un numero');
frontend/src/app/features/administracion/roles/roles.component.css:127:.descripcion { margin: 0; color: var(--tinta); font-size: 15px; }
frontend/src/app/features/administracion/roles/roles.component.html:10:        <p class="gris">Define que puede hacer cada perfil de tu empresa. Toca un rol para ver mas.</p>
frontend/src/app/features/administracion/roles/roles.component.html:42:            <label for="descripcion">Descripcion</label>
frontend/src/app/features/administracion/roles/roles.component.html:43:            <input id="descripcion" type="text" formControlName="descripcion"
frontend/src/app/features/administracion/roles/roles.component.html:51:            @for (p of permisosCatalogo(); track p.codigo) {
frontend/src/app/features/administracion/roles/roles.component.html:52:              <label class="permiso" [class.marcado]="seleccionados().has(p.codigo)">
frontend/src/app/features/administracion/roles/roles.component.html:54:                       [checked]="seleccionados().has(p.codigo)"
frontend/src/app/features/administracion/roles/roles.component.html:55:                       (change)="alternarPermiso(p.codigo)" />
frontend/src/app/features/administracion/roles/roles.component.html:57:                  <strong>{{ p.codigo }}</strong>
frontend/src/app/features/administracion/roles/roles.component.html:58:                  <small>{{ p.descripcion }}</small>
frontend/src/app/features/administracion/roles/roles.component.html:108:                <p class="descripcion">{{ rol.descripcion || 'Sin descripcion.' }}</p>
frontend/src/app/features/administracion/roles/roles.component.html:112:                  @for (codigo of rol.permisos; track codigo) {
frontend/src/app/features/administracion/roles/roles.component.html:113:                    <span class="chip">{{ codigo }}</span>
frontend/src/app/features/administracion/roles/roles.component.ts:36:    descripcion: ['', [Validators.maxLength(200)]],
frontend/src/app/features/administracion/roles/roles.component.ts:64:    this.formulario.reset({ nombre: '', descripcion: '' });
frontend/src/app/features/administracion/roles/roles.component.ts:76:    this.formulario.reset({ nombre: rol.nombre, descripcion: rol.descripcion });
frontend/src/app/features/administracion/roles/roles.component.ts:88:  alternarPermiso(codigo: string): void {
frontend/src/app/features/administracion/roles/roles.component.ts:91:      if (copia.has(codigo)) {
frontend/src/app/features/administracion/roles/roles.component.ts:92:        copia.delete(codigo);
frontend/src/app/features/administracion/roles/roles.component.ts:94:        copia.add(codigo);
frontend/src/app/features/auth/login/login.component.html:14:      <div class="aviso" [class.aviso-error]="e.codigo !== 'CUENTA_BLOQUEADA'"
frontend/src/app/features/auth/login/login.component.html:15:           [class.aviso-alerta]="e.codigo === 'CUENTA_BLOQUEADA'" role="alert">
frontend/src/app/features/auth/login/login.component.html:16:        @switch (e.codigo) {
frontend/src/app/features/auth/restablecer-password/restablecer-password.component.html:36:            <p class="ayuda">Minimo 8 caracteres, con mayuscula, minuscula y numero.</p>
frontend/src/app/features/catalogo/clientes/clientes.component.html:56:              <p class="mensaje-error">El numero de documento es obligatorio.</p>
frontend/src/app/features/catalogo/clientes/clientes.component.html:70:            <label for="telefono">Telefono</label>
frontend/src/app/features/catalogo/clientes/clientes.component.html:71:            <input id="telefono" type="tel" formControlName="telefono" placeholder="3105556666" />
frontend/src/app/features/catalogo/clientes/clientes.component.html:128:                  <span class="linea-dato gris">{{ c.telefono }}</span>
frontend/src/app/features/catalogo/clientes/clientes.component.ts:44:    telefono: ['', [Validators.maxLength(20)]],
frontend/src/app/features/catalogo/clientes/clientes.component.ts:82:      email: '', telefono: '', ciudad: '', usuario_id: '',
frontend/src/app/features/catalogo/clientes/clientes.component.ts:95:      telefono: cliente.telefono,
frontend/src/app/features/catalogo/productos/productos.component.html:46:          <label for="descripcion">Descripcion</label>
frontend/src/app/features/catalogo/productos/productos.component.html:47:          <textarea id="descripcion" formControlName="descripcion" rows="2"
frontend/src/app/features/catalogo/productos/productos.component.html:55:              <option value="">Sin categoria</option>
frontend/src/app/features/catalogo/productos/productos.component.ts:34:    descripcion: ['', [Validators.maxLength(500)]],
frontend/src/app/features/catalogo/productos/productos.component.ts:80:      nombre: '', sku: '', descripcion: '', categoria_id: '',
frontend/src/app/features/catalogo/productos/productos.component.ts:92:      descripcion: producto.descripcion,
frontend/src/app/features/catalogo/productos/productos.component.ts:159:        if (e.codigo === 'PRODUCTO_CON_VENTAS') {
frontend/src/app/features/configuracion/configuracion.component.ts:8:  selector: 'app-configuracion',
frontend/src/app/features/configuracion/configuracion.component.ts:15:          <p class="descripcion">Informacion de tu cuenta y de la empresa.</p>
frontend/src/app/features/configuracion/configuracion.component.ts:41:          <p class="nota">Mas opciones de configuracion disponibles proximamente.</p>
frontend/src/app/features/configuracion/configuracion.component.ts:61:      .descripcion { margin: 0 0 var(--e5); color: var(--gris); }
frontend/src/app/features/dashboard/dashboard.component.ts:14:          <p>Desde aqui administraras inventario, ventas y reportes de tu negocio.</p>
frontend/src/app/features/dashboard/dashboard.component.ts:65:    { titulo: 'Inventario', texto: 'Control de stock, alertas de minimos y movimientos de producto.' },
frontend/src/app/features/dashboard/dashboard.component.ts:66:    { titulo: 'Ventas y facturacion', texto: 'Registra ventas en el mostrador y genera la factura al instante.' },
frontend/src/app/features/home/home.component.ts:18:      titulo: 'Inventario al dia',
frontend/src/app/features/home/home.component.ts:23:      titulo: 'Ventas y facturacion',
frontend/src/app/features/registro/registro.component.html:78:            <p class="ayuda">Minimo 8 caracteres, con mayuscula, minuscula y numero.</p>
frontend/src/app/shared/layout/auth-shell/auth-shell.component.html:5:      <span class="lema">Tu mejor aliado en la gestion empresarial</span>
frontend/src/app/shared/layout/panel-shell/panel-shell.component.ts:53:                  <a routerLink="/configuracion" (click)="cerrarMenu()">Configuracion</a>
frontend/src/app/shared/layout/site-footer/site-footer.component.ts:10:          <p>Tu mejor aliado en la gestion empresarial.</p>
```

**Nota de lectura:** buena parte de estas coincidencias son identificadores de código (`codigo:`, `descripcion:`, `telefono:` como nombres de campo/propiedad TypeScript) y no texto que un usuario final lea sin tildes — no se puede saber sólo con este grep cuáles son errores ortográficos reales visibles en pantalla y cuáles son nombres de variable. Las líneas que sí son texto visible sin tildes (candidatas reales a revisar) son, por ejemplo: `dashboard.component.ts:14` ("Desde aqui administraras..."), `dashboard.component.ts:65-66`, `configuracion.component.ts:41` ("Mas opciones... proximamente"), `auth-shell.component.html:5` y `site-footer.component.ts:10` ("Tu mejor aliado en la gestion empresarial"), y los `<label>`/`<p class="ayuda">` de los formularios ("Telefono", "Descripcion", "Minimo 8 caracteres..."). No se corrigió nada, como se pidió.

---

## 9. Deuda y riesgos

### 9.1 Riesgo de fuga entre tenants — CONFIRMADO por lectura de código

El modelo `Rol` (`backend/cuentas/models.py:11-30`) **no tiene FK a `Empresa`** — es una tabla global, única por `nombre` (línea 16). Sin embargo, la fase 2 ("administración de seguridad") permite a **cualquier ADMINISTRADOR de cualquier empresa** crear roles personalizados adicionales a los 3 del sistema (`RolesSeguridadView.post`, `backend/cuentas/views_admin.py:180-193`). Verificado leyendo cada consulta a `Rol` en `backend/cuentas/views_admin.py` y `backend/cuentas/serializers_admin.py`: **ninguna filtra por empresa**:

- `RolesSeguridadView.get` (`views_admin.py:176`) — `Rol.objects.prefetch_related(...).order_by("nombre")`: lista **todos** los roles de **todas** las empresas de la plataforma.
- `RolDetalleView.obtener_rol` (`views_admin.py:201-202`) — `Rol.objects.filter(id=id)...`: cualquier ADMINISTRADOR puede hacer `GET/PUT/PATCH/DELETE` sobre un rol creado por otra empresa con solo conocer (o adivinar/enumerar vía el propio `GET` de la lista) su UUID.
- `RolClonarView.post` (`views_admin.py:277-299`) — clona cualquier rol por id, de cualquier empresa.
- `validar_rol_existe` (`serializers_admin.py:26-30`) y `RolEscrituraSerializer.validate_nombre` (`serializers_admin.py:93-100`) — validan existencia/unicidad de nombre **contra la tabla completa**, no por empresa. Esto además significa que si la Empresa A ya usó el nombre "SUPERVISOR" para un rol personalizado, la Empresa B **no puede** crear un rol con ese mismo nombre (colisión entre tenants no relacionados).
- Consecuencia adicional: como `Perfil.rol` es una FK compartida (`cuentas/models.py:71`), si el ADMINISTRADOR de la Empresa B edita los permisos de un rol que en realidad "pertenece" (fue creado por) la Empresa A pero que quedó asignado por error/enumeración a un usuario de B, **cambia silenciosamente los permisos también para los usuarios de la Empresa A** que tengan ese mismo rol asignado.
- **No está cubierto por tests:** `BaseSeguridadTest.setUpTestData` (`backend/cuentas/tests.py:244-251`) crea una única `Empresa`. Ninguna clase de test en `backend/cuentas/tests.py` crea una segunda empresa para verificar aislamiento en `/api/seguridad/roles/` (contrástese con `backend/core/tests.py:66-70`, que sí crea una segunda `Empresa` pero solo para probar una constraint de modelo a nivel de `Cliente`, no para probar aislamiento vía API). Es decir: el hueco existe en el código **y** no hay ningún test que lo hubiera detectado.
- Los endpoints de **usuarios** (`UsuariosSeguridadView` y relacionados) y de **clientes/productos/categorías** (`views_catalogo.py`) sí filtran correctamente por `request.user.perfil.empresa` en cada consulta (ver citas de la sección 2) — el problema está acotado a `Rol`.

### 9.2 Datos hardcodeados / placeholder

- Footer compartido (`frontend/src/app/shared/layout/site-footer/site-footer.component.ts`): teléfono `+57 300 123 4567` (línea 15) y correo `soporte@intersoft.co` (línea 14) hardcodeados y, a juzgar por el formato, ficticios/de ejemplo.
- Mismo componente, línea 19: `<p class="redes">Facebook · Instagram · LinkedIn</p>` — es **texto plano, no son enlaces** (no hay ningún `<a href>` alrededor; confirmado también que no existe ningún `href="#"` en `frontend/src` — búsqueda sin resultados — así que no es ni siquiera un enlace roto, es directamente texto sin interactividad).
- `DEFAULT_FROM_EMAIL = 'no-responder@intersoft.co'` — `backend/intersoft/settings.py:129`. Coherente con el dominio del correo del footer, pero igualmente hardcodeado en settings en vez de por variable de entorno (contrástese con `SECRET_KEY`, `DB_*`, `CORS_ALLOWED_ORIGINS`, que sí usan `config(...)` de `python-decouple`).
- `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` (`settings.py:128`) — los correos (incluida la recuperación de contraseña) **no se envían de verdad**, solo se imprimen en la consola del servidor. No hay SMTP configurado en ningún entorno de este repo.

### 9.3 Botones/enlaces sin destino real

- Dashboard (`frontend/src/app/features/dashboard/dashboard.component.ts:22`): 3 tarjetas de módulo (Inventario, Ventas y facturación, Reportes) con una insignia `<span class="estado insignia-pulso">Proximamente</span>` — no son enlaces ni botones (no tienen `routerLink` ni `(click)`), son puramente decorativas. Coherente con la sección 4: esos módulos no tienen backend detrás todavía.
- `configuracion.component.ts:41`: `<p class="nota">Mas opciones de configuracion disponibles proximamente.</p>` — mismo patrón, aviso textual sin acción real detrás.

### 9.4 Otras observaciones de deuda técnica (no se corrigieron, solo se anotan)

- `backend/core/signals.py:9-13` — la alerta de stock bajo usa `print()` directo en vez del sistema de logging ya configurado en `settings.py:135-168` (que sí tiene handlers de archivo rotativo). El `print()` no queda registrado en `backend/logs/intersoft.log`; solo es visible en la consola del proceso en el momento en que ocurre.
- `backend/tests/README.md:5` da una instrucción de ejecución (`pytest`) que no corresponde a lo que hay instalado ni a cómo se ejecutaron realmente los tests en esta auditoría (sección 7) — puede confundir a alguien nuevo en el proyecto.
- Las rutas de `core/urls_catalogo.py` no tienen `name=` (sección 5), a diferencia de las de `cuentas/urls.py` y `cuentas/urls_admin.py` que sí lo tienen — inconsistencia menor de estilo entre apps, sin impacto funcional mientras nadie use `reverse()` sobre esas rutas (no se encontró ningún `reverse()` apuntando a `core.urls_catalogo` en el código ni en los tests).
- `RolClonarView` (`views_admin.py:273-299`) no está protegido contra colisión de nombre entre tenants distintos de forma más robusta que un sufijo `(COPIA)`/`(COPIA) 2`... — es una consecuencia directa del mismo problema de 9.1 (unicidad global del nombre de `Rol`).

---

## PREGUNTAS PARA DANIEL

1. **`SPEC.md` no existe en el repositorio.** ¿Se te olvidó añadirlo/commitearlo, o el rediseño de dashboard que planeas es para el componente Angular (`frontend/src/app/features/dashboard/dashboard.component.ts`), no para nada dentro de `backend/`? Toda esta auditoría asumió que "el proyecto" a auditar era `backend/` porque el enunciado habla de `templates/`, `static/`, RBAC con decoradores Django, etc. — pero el dashboard real que existe hoy vive 100% en Angular y no llama a ningún endpoint del backend. Si el rediseño es del dashboard Angular, esta auditoría cubre la mitad equivocada del repo y convendría repetirla centrada en `frontend/`.
2. **¿El hallazgo de la sección 9.1 (roles compartidos entre tenants) era conocido?** Está confirmado por lectura directa de código (ninguna consulta a `Rol` filtra por empresa) pero no lo probé en vivo contra una base de datos con dos empresas reales y dos usuarios ADMINISTRADOR distintos — quedó fuera del alcance de "solo lectura" de este turno. ¿Quieres que en un turno futuro escriba un test que lo demuestre end-to-end antes de decidir si se corrige?
3. **`backend/tests/README.md` dice "usa pytest"** pero ni `pytest` ni `pytest-django` están en `requirements.txt` ni instalados. ¿Es intención migrar a pytest en algún momento, o el README quedó desactualizado y el comando correcto sigue siendo `python manage.py test`?
4. **¿Vas a construir las API de `Venta`/`DetalleVenta`/`MovimientoInventario`/`Notificacion` antes o como parte del rediseño del dashboard?** Hoy esos 4 modelos existen en la base de datos y en el Django Admin, pero no tienen ni un solo endpoint REST — cualquier dashboard que muestre ventas, kardex o notificaciones necesitará esa capa nueva primero.
5. **¿Los 3 roles del sistema (`ADMINISTRADOR`/`EMPLEADO`/`CLIENTE`) son los únicos que quieres soportar en el rediseño,** o el rediseño del dashboard debe contemplar que cada empresa tenga roles 100% personalizados (lo que agravaría el problema de 9.1 si no se corrige antes)?
