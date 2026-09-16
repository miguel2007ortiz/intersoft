# QA — correcciones de las Fases 2, 2.1 y 2.2

Registro de lo que se midió, lo que se corrigió y lo que quedó descartado, para
no volver a investigar lo mismo. Rama: `fix/qa-fase-2-seguridad`.

---

## BUG-05 — «el login exitoso tarda entre 8 y 29 s» — no se reproduce

### Lo que se midió

Instrumentación temporal con `time.perf_counter()` en cada paso del camino
exitoso de `LoginView`, contra MySQL 8.0.30 local. Retirada después de medir.

| Paso | Tiempo |
|---|---|
| **Total del login exitoso** | **645 ms** / 3 consultas |
| Total del login fallido (contraseña incorrecta) | 644 ms / 4 consultas |
| Emisión del token (`RefreshToken.for_user`) | 0,1 ms |
| Reinicio de intentos | 0,0 ms |
| `INSERT` en `actividad_usuario` | 1–3 ms |
| Serializar el contexto (empresa, rol) | 0,0 ms |
| `GET /auth/me/` | 8,6 ms / 5 consultas |

**El coste está casi todo en un sitio**: los ~640 ms son el hash PBKDF2 que
`authenticate()` calcula para verificar la contraseña
(`pbkdf2_sha256`, 1 000 000 de iteraciones — el valor por omisión de Django
5.2; el proyecto no define `PASSWORD_HASHERS`). Todo lo que ocurre después de
autenticar suma unos 3 ms.

Descartado, por tanto, todo lo que el ticket proponía como causa: no hay
señales sobre los modelos de autenticación, el middleware de auditoría sale
temprano (en el POST del login `request.user` es anónimo), no hay llamadas de
red, y la tabla de auditoría ya no ordena por `-fecha` sin índice.

### El «fallido: 99 ms» del ticket es una comparación falsa

Un fallo de contraseña costaba **lo mismo** que el éxito: 644 ms, porque
también calcula el hash. Los 99 ms solo salen de los caminos que retornaban
**antes** de verificar la contraseña: cuenta bloqueada (423), cuenta
desactivada (403) o datos inválidos (400).

Es decir: esa cifra del ticket no era un problema de rendimiento, era el
oráculo de tiempo del BUG-19. Quien medía «99 ms» estaba midiendo un rechazo
que nunca llegó a hashear, y de paso comprobando que el servidor filtraba por
tiempo si el correo existía. Ya está cerrado: los dos caminos hashean.

### Medición contra la base de desarrollo real (evidencia)

La medición anterior usa la base de pruebas, que el runner crea limpia. Esta se
hizo contra `intersoft1_db`, la base de desarrollo desfasada, con `runserver` y
`curl` — es decir, el mismo camino que recorre el navegador.

Respaldo previo con `mysqldump --single-transaction` guardado en
`backend/backups/` (directorio ignorado por git). No se ejecutó `seed_demo`.

**Antes de migrar** (`cuentas` en `0001_initial`, sin `intersoft_cache`):

| Intento | HTTP | Tiempo |
|---|---|---|
| 1 | 500 | 35 ms |
| 2 | 500 | 33 ms |
| 3 | 500 | 47 ms |

Causa, literal del log del servidor:

```
ProgrammingError: (1146, "Table 'intersoft1_db.intersoft_cache' doesn't exist")
```

El fallo ocurre **antes de entrar a la vista**: el throttle por IP consulta el
caché, el caché está configurado como `DatabaseCache` en `backend/.env` y la
tabla no existe. Ni siquiera se llega a verificar la contraseña.

**Después de `migrate` + `crear_cache` + `seed_roles`**:

| Intento | HTTP | Tiempo |
|---|---|---|
| 1 | 200 | 567 ms |
| 2 | 200 | 493 ms |
| 3 | 200 | 506 ms |

### Corrección: la base desfasada NO explica los 8–29 s

La hipótesis que estaba escrita aquí era que el esquema incompleto encarecía
cada login por el coste de una excepción con traceback. **La medición la
refuta**: la base desfasada produce un **500 en 35 ms**, no un 200 lento. Falla
rápido y falla del todo.

Sigue siendo un problema real —con la base así el login no funciona en
absoluto— pero es un problema distinto del del ticket, y lo corrige el mismo
`migrate` + `crear_cache`.

**Los 8–29 s siguen sin reproducirse.** Con la base al día el login exitoso
tarda ~500 ms extremo a extremo por HTTP. Lo que queda por descartar está
fuera del backend, y para investigarlo hace falta una medición del entorno
donde se observó:

- La secuencia real del navegador es `POST /login/` **más** `GET /me/`
  (`AuthService.login` encadena las dos). Un cortafuegos o antivirus que
  inspeccione la conexión puede añadir segundos a la segunda petición.
- `runserver` es monohilo por defecto: si otra petición está en curso, la del
  login espera. No aplica a producción (gunicorn), sí a una demo local.
- Medir con la pestaña de red del navegador y separar los tiempos de las dos
  peticiones diría en cuál está el tiempo. Sin ese dato no hay más que buscar
  en el código.

### Lo que sí se aplicó

- `select_related` en el login y en `/auth/me/` para traer perfil, empresa y
  rol en una consulta (antes: tres consultas extra).
- Índice `(usuario, -fecha)` en `actividad_usuario`
  (`cuentas/migrations/0011`): la tabla solo se lee por «actividad de este
  usuario, lo más reciente primero», y sin índice eso era un *filesort* sobre
  toda la tabla en cuanto crecía el historial.
- Techo de consultas fijado con `assertNumQueries`: **4** para el login
  (resolver identidad, `authenticate`, `UPDATE last_login`, `INSERT` de
  auditoría) y **3** para `/auth/me/`.

**Estado: ~700 ms y 4 consultas en local.** Por debajo del objetivo de 1 s. No
baja más sin reducir las iteraciones del hasher, que es una decisión de
seguridad y no de rendimiento.

---

## Revisión de entorno (sin cambios de código)

### 1. `DB_HOST`: ya es `127.0.0.1`, no hace falta cambiar nada

En Windows, `localhost` se resuelve primero a `::1` (IPv6). Si MySQL solo
escucha en IPv4, cada conexión paga un intento fallido antes de reintentar por
IPv4 — y como `CONN_MAX_AGE` no está definido (Django usa 0: conexión nueva y
cerrada en **cada petición**), ese coste se paga en todas.

Revisado: no aplica. `DB_HOST` vale `127.0.0.1` en los tres sitios —
`intersoft/settings.py` (valor por omisión), `backend/.env` y el CI. El
`docker-compose.yml` usa `db`, el nombre del servicio, que resuelve dentro de
la red del compose.

Recomendación, por si alguien lo cambia: mantener `127.0.0.1` y **no** poner
`localhost`. Si algún día el despliegue paga latencia de conexión, la palanca
es `CONN_MAX_AGE` (conexiones persistentes), que hoy no está configurado.

### 2. Reescritura del hash en el primer login

`AbstractBaseUser.check_password()` le pasa a `check_password` un *setter*:
si el hash guardado no coincide con la configuración actual del hasher
(algoritmo distinto, o distinto número de iteraciones), Django lo **reescribe**
con la configuración nueva. Eso cuesta un hash extra y un
`save(update_fields=["password"])`, **una sola vez por cuenta**, en su primer
login después del cambio.

Cuándo aparece: al subir de versión de Django (cada versión sube las
iteraciones por omisión) o al tocar `PASSWORD_HASHERS`. El proyecto no define
`PASSWORD_HASHERS`, así que hereda el valor de la versión instalada
(`pbkdf2_sha256`, 1 000 000 de iteraciones en Django 5.2).

Consecuencia práctica: tras actualizar Django, el primer login de cada persona
puede costar el doble (~1,3 s) y los siguientes volver a ~650 ms. No es un
problema a corregir; es algo a no confundir con una regresión. Y explica un
pico inicial, no 8–29 s.

### 3. Qué base usa cada entorno, y cómo poner la de desarrollo al día

| Entorno | Base | Host:puerto | Origen de la configuración |
|---|---|---|---|
| Desarrollo local (Laragon) | `intersoft1_db` | `127.0.0.1:3306` | `backend/.env` |
| Docker Compose | `intersoft1_db` | `db:3306` (publicado en `3307`) | `docker-compose.yml` |
| CI (GitHub Actions) | `intersoft1_db` | `127.0.0.1:3306` | `.github/workflows/ci.yml` |
| `manage.py test` | `test_intersoft1_db` | igual que el entorno | La crea y la destruye el runner |

Las pruebas **nunca** tocan `intersoft1_db`: Django crea `test_intersoft1_db`
aparte. Por eso la base de desarrollo puede estar desfasada sin que la suite se
queje.

Estado observado de `intersoft1_db` antes de esta rama: aplicada solo
`cuentas.0001_initial`, con 11 migraciones de `cuentas` pendientes. Faltaban
`actividad_usuario`, `rol`, `permiso`, `rol_permiso` e `intersoft_cache`, y
arrastra una tabla `core_usuario` de un modelo que ya no existe. **Con ese
esquema el login devolvía 500**, ver la medición de arriba. Ya está al día.

Nota sobre el caché en local: `backend/.env` fija
`CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache`, que exige haber
corrido `crear_cache`. Desde esta rama el valor por omisión con `DEBUG=True` es
`LocMemCache`, que no necesita tabla; comentar esa línea del `.env` evita
volver a tropezar con el mismo 500.

Para ponerla al día (con el MySQL de Laragon arriba, desde `backend/` y con el
entorno virtual activado):

```bash
python manage.py migrate            # esquema al dia (incluye 0012)
python manage.py crear_cache        # crea la tabla intersoft_cache
python manage.py seed_roles         # roles base y sus permisos
python manage.py seed_demo          # opcional: datos de demostracion
python manage.py monitor            # comprueba BD, migraciones, cache y disco
```

Si `migrate` se detiene en `cuentas.0012_email_unico_sin_mayusculas`, es que hay
correos o usuarios repetidos ignorando mayúsculas. El propio error los lista;
para verlos sin migrar:

```bash
python manage.py verificar_emails_duplicados
```

Deja una sola cuenta por correo (cambia o vacía el de las demás) y repite.

`0012` **exige MySQL 8.0.13 o superior** (la versión que introdujo los índices
funcionales) y **no puede aplicarse en MariaDB**, que no los soporta en ninguna
versión. La migración comprueba motor y versión y aborta diciendo qué falta, en
vez de dejar salir un error de sintaxis de SQL. En MariaDB habría que sustituir
los índices funcionales por una columna generada `email_lower` con un `UNIQUE`
normal encima.

---

## Rotación de `SECRET_KEY`

Ver `docs/CHECKLIST-SEGURIDAD.md`. Resumen: `SIMPLE_JWT` no define
`SIGNING_KEY`, así que los JWT se firman con `SECRET_KEY`; rotarla invalida
todos los tokens emitidos y cierra la sesión de todo el mundo.
