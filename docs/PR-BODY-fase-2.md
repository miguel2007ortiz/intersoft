# QA Fase 2 — seguridad de autenticación y aislamiento multiempresa

Cierra BUG-05, BUG-09, BUG-13, BUG-18, BUG-19 y BUG-27, más las revisiones 2.1
y 2.2. 9 commits, 29 archivos.

## Resumen por bug

### BUG-09 — el login resolvía una identidad ambigua

El perfil se elegía por correo con
`Perfil.objects.filter(usuario__email__iexact=email).first()`, en paralelo a lo
que devolvía `authenticate()`. Con dos perfiles que compartieran correo, el
contexto de sesión (empresa, rol, permisos) y el conteo de intentos fallidos
podían acabar en una cuenta distinta de la que se estaba abriendo.

- La identidad se resuelve **una sola vez** contra `auth_user`, y el perfil sale
  del `OneToOne` del usuario ya autenticado.
- Unicidad garantizada en la base **sin depender de la collation**: índices
  `UNIQUE` funcionales sobre `LOWER(email)` y `LOWER(username)`. El `UNIQUE`
  plano anterior solo ignoraba mayúsculas porque la collation por omisión de
  MySQL lo hace; en una base `utf8mb4_bin` el problema volvía. Verificado
  empíricamente contra una tabla con esa collation.
- `authenticate()` autentica contra `username` (el `USERNAME_FIELD`), no contra
  `email`: por eso ambas columnas llevan la misma garantía.
- `cuentas/identidad.py` centraliza la normalización y la búsqueda por
  `LOWER()`, y reemplaza los `email__iexact` repartidos por vistas y
  serializers.

### BUG-19 — el login permitía enumerar correos

- El 401 es idéntico exista o no el correo: mismo código, mismo cuerpo, y **sin
  `intentos_restantes`**. Una cuenta desactivada también devuelve ese 401.
- En el último intento antes del bloqueo se manda un `aviso` genérico, sin
  cifras, igual para correos inexistentes.
- El 423 llega también para correos que no existen, con `desbloqueo_en`.
- Sin diferencia de tiempo: los dos caminos calculan el hash.
- **Sin oráculo residual por IP**: el contador de correos inexistentes se
  indexaba por `correo + IP` mientras el bloqueo de cuenta real es global, así
  que cinco intentos repartidos entre cinco IPs distinguían un correo
  registrado de uno que no. Ahora la clave es solo el correo.
- **Límite por IP en el login** (`THROTTLE_LOGIN`, 10/minuto). Cada intento
  cuesta un hash PBKDF2 de ~650 ms; sin tope es denegación de servicio. No
  bloquea cuentas.
- La identificación del cliente la resuelve DRF con `NUM_PROXIES` (0 por
  omisión). El `get_ident` propio leía siempre el último `X-Forwarded-For`, lo
  que sin proxy delante hacía el límite evadible con una cabecera inventada.

### BUG-13 — Roles contaba 5 usuarios y Usuarios mostraba 2

- **Roles era la pantalla mala.** Los roles base son globales (`empresa=None`),
  así que `Count("perfiles")` sumaba perfiles de todos los tenants. Usuarios ya
  filtraba bien. Corregido también el conteo de respaldo del serializer y el
  del `DELETE` de rol.
- **Escalada entre tenants, prioridad alta.** La guarda de roles del sistema
  comparaba el nombre contra `{ADMINISTRADOR, EMPLEADO, CLIENTE}`. Un rol
  global con cualquier otro nombre era editable, repermisable y borrable por el
  administrador de **cualquier** empresa, que así alteraba la autorización de
  toda la plataforma. La condición correcta es `rol.empresa_id is None` →
  403 `ROL_DEL_SISTEMA`.
- `Rol.de_nombre()` creaba un rol global con el nombre que se le pasara; ahora
  solo acepta los tres base y, si no, lanza `ValueError` indicando cómo crear
  un rol propio de empresa.
- El rol `CLIENTE` con 0 permisos **es intencional**: las rutas del marketplace
  no dependen de `RolPermiso`.
- Barrido de aislamiento: sin `.objects.all()` sin filtrar en vistas ni
  serializers. Los 22 candidatos del escaneo resultaron acotados de forma
  indirecta o cross-empresa por diseño (catálogo público del marketplace).

### BUG-05 — «el login tarda entre 8 y 29 s» — no se reproduce

Medido antes de tocar nada: **645 ms y 3 consultas**, de los que ~640 ms son el
hash PBKDF2 de `authenticate()`. Todo lo posterior suma ~3 ms.

El «fallido: 99 ms» del ticket no era comparable: un fallo de contraseña costaba
los mismos 644 ms. Los 99 ms salían de los retornos previos a verificar la
contraseña, es decir el propio oráculo de tiempo del BUG-19.

Medido después contra la base de desarrollo real: **sin migrar da 500 en 35 ms**
(`Table 'intersoft1_db.intersoft_cache' doesn't exist`), y migrada da **200 en
~500 ms**. Eso refuta la hipótesis de que la base desfasada encarecía el login:
lo rompe, no lo ralentiza.

Aplicado igualmente: `select_related` en login y `/auth/me/`, índice
`(usuario, -fecha)` en `actividad_usuario`, y techos con `assertNumQueries`
(4 en login, 3 en `/auth/me/`).

Detalle completo y tablas de medición en
[`docs/QA-correcciones.md`](docs/QA-correcciones.md).

### BUG-18 — `DEBUG=True` publicaba el URLconf

- Con `DEBUG=False`, solo `JSONRenderer` (el `BrowsableAPIRenderer` de DRF
  publica formularios y campos de los serializers) y `handler404`/`handler500`
  que devuelven JSON genérico.
- **`.env.example` traía una `SECRET_KEY` que pasaba el guard de producción**:
  no empezaba por `django-insecure-` ni coincidía con el placeholder. Copiar la
  plantilla y poner `DEBUG=False` dejaba la app firmando JWT con una clave que
  está en el repo. Ahora la plantilla va vacía y el arranque rechaza cualquier
  clave con marcador de «sin cambiar», incluida la del `docker-compose.yml`.
- Búsqueda en el historial: la clave solo aparece en `.env.example`,
  `settings.py` y `docker-compose.yml`. **Ningún `.env` real se versionó nunca.**
  Historial no reescrito.
- `SIMPLE_JWT` no define `SIGNING_KEY`: hereda `SECRET_KEY`, así que rotarla
  cierra la sesión de todo el mundo. Procedimiento en
  [`docs/CHECKLIST-SEGURIDAD.md`](docs/CHECKLIST-SEGURIDAD.md) §1.b.
- `python manage.py check --deploy` con `DEBUG=False`: **sin advertencias**.

### BUG-27 — «último acceso» vacío en todas las filas

`authenticate()` no toca `last_login`; el receptor que lo actualiza cuelga de
`user_logged_in`, que solo dispara `django.contrib.auth.login()` (sesiones), y
esta API es por JWT. `last_login` quedaba en `NULL` para siempre. El login
exitoso llama ahora a `update_last_login`.

## Cambios de contrato

Contrato completo en **[`docs/contratos/auth.md`](docs/contratos/auth.md)**.

| Antes | Ahora |
|---|---|
| `usuario.id` = id del **Perfil** (UUID) | `usuario.id` = id de **`auth_user`**; `usuario.perfil_id` aparte |
| 401 con `intentos_restantes` | 401 sin ese campo; `aviso` genérico solo en el último intento |
| Cuenta desactivada → 403 `USUARIO_INACTIVO` | → 401 genérico (el 403 solo con la contraseña ya probada) |
| Rol del sistema → 400 `ROL_SISTEMA_LECTURA_ONLY` | → 403 `ROL_DEL_SISTEMA`, y por `empresa=None`, no por nombre |
| `/auth/me/` sin `perfil_id` | incluye `id` y `perfil_id`, mismas claves que el login |

Frontend adaptado: `auth.model.ts`, `auth.service.ts` y la plantilla de login.
`cargarMe()` ahora refresca también el usuario guardado — antes
`intersoft.usuario` se escribía solo en el login, así que un cambio de rol o de
empresa no llegaba hasta cerrar sesión.

En la pantalla de Roles, los roles del sistema ya no ofrecen **Editar** ni
**Eliminar**, se etiquetan «Rol del sistema» y explican que la vía es clonarlos.

## Migraciones

| Migración | Qué hace |
|---|---|
| `cuentas/0010_verificar_email_unico` | Aborta si hay correos duplicados, listando cuáles y con qué ids; asegura el índice de `0005` si falta |
| `cuentas/0011_actividadusuario_actividad_usuario_fecha_idx` | Índice `(usuario, -fecha)` en `actividad_usuario` |
| `cuentas/0012_email_unico_sin_mayusculas` | Sustituye el `UNIQUE` de `email` por índices funcionales sobre `LOWER(email)` y `LOWER(username)`; normaliza a minúsculas las filas heredadas |

**`0012` exige MySQL ≥ 8.0.13** (los índices funcionales se añadieron ahí) y
**no puede aplicarse en MariaDB**, que no los soporta. La migración comprueba
motor y versión y aborta con un mensaje que dice qué falta.

Todas son reversibles. Ninguna borra datos.

## Pasos de despliegue

1. **Antes de migrar**, comprobar que no hay identidades ambiguas:
   ```bash
   python manage.py verificar_emails_duplicados
   ```
   Si falla, lista correo/usuario repetido con sus `auth_user.id`. Deja una sola
   cuenta por cada uno y repite. `0012` aborta si no.

2. Migrar y crear la tabla de caché:
   ```bash
   python manage.py migrate
   python manage.py crear_cache
   ```
   `crear_cache` es **obligatorio**: con `DEBUG=False` el caché es
   `DatabaseCache` y de él cuelgan el límite por IP y el conteo de intentos.

3. Variables de entorno nuevas (todas opcionales, con valores por omisión
   seguros — ver `backend/.env.example`):

   | Variable | Por omisión | Cuándo cambiarla |
   |---|---|---|
   | `NUM_PROXIES` | `0` | **`1` si hay un nginx delante.** Con 0 se ignora `X-Forwarded-For` |
   | `THROTTLE_LOGIN` | `10/minute` | Solo si el despliegue lo exige |
   | `CACHE_BACKEND` | según `DEBUG` | Apuntar a Redis con varios workers |

   Si `SECRET_KEY` es una de las públicas del repo, la app **no arranca**: hay
   que generar una nueva (rotarla cierra todas las sesiones).

4. Desplegar el frontend junto con el backend: el contrato de `/api/auth/`
   cambió y las dos partes tienen que ir a la vez.

5. Verificar: un login completo y `GET /api/ruta-inexistente/` devolviendo 404
   JSON sin `URLconf` en el cuerpo.

## Configuración local

`backend/.env` (no versionado) fija
`CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache`, y ese valor
**sobrescribe** el nuevo valor por omisión que introduce esta rama.

Con esa línea activa, el desarrollo local exige haber ejecutado
`python manage.py crear_cache`; si la tabla `intersoft_cache` no existe, **el
login devuelve 500** antes de entrar a la vista, porque el límite por IP
consulta el caché. Es el fallo que quedó medido en
[`docs/QA-correcciones.md`](docs/QA-correcciones.md).

Para desarrollo, lo más simple es **comentar esa línea** en tu `.env`:

```diff
-CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache
+#CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache
```

Así el valor por omisión con `DEBUG=True` es `LocMemCache`, que no necesita
tabla. En `DEBUG=False` el valor por omisión sigue siendo `DatabaseCache` y
`crear_cache` continúa siendo obligatorio (ver los pasos de despliegue).

## Verificación

| | |
|---|---|
| Backend `manage.py test` (MySQL 8.0.30) | **691 tests, OK** |
| `ruff check` | limpio |
| `manage.py check --deploy` (`DEBUG=False`) | sin advertencias |
| Frontend `npm run lint` | limpio (ESLint + Prettier) |
| Frontend `npm run test:ci` | **105 tests, OK** |
| `ng build` | correcto |

## Nota para el revisor

El primer commit (`fd15370`) arrastra el trabajo de la Fase 2, que no se había
commiteado antes de empezar la revisión; su mensaje lo dice. Los demás van por
punto.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
