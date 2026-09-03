# Backend

Este directorio contiene la lógica del servidor y la gestión de datos (Django REST + MySQL 8).

## Requisitos
- Python 3.12 (verificado en 3.12.x).
- MySQL 8 (8.0.36+), en desarrollo suele usarse Laragon.
- Node.js no es necesario para el backend (solo es para compilar el frontend).
- Dependencias **pinneadas** en `requirements.txt` (versiones exactas `==`
  verificadas con la suite de 241 tests). Instalar con `pip install -r requirements.txt`.
  - `mysqlclient` compila en Linux/macOS (requiere `libmysqlclient-dev`);
    en Windows se usa el fallback **PyMySQL** (activado automáticamente por
    `intersoft/__init__.py`).
  - El runtime actual (Windows, PyMySQL): Django 5.2.17, DRF 3.18.0,
    simplejwt 5.5.1, cors-headers 4.9.0, decouple 3.8, Pillow 11.2.1.

## Instalación
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
```

## Configuración de entorno
1. Copia la plantilla y ajusta los valores:
   - Windows: `copy .env.example .env`
   - Mac/Linux: `cp .env.example .env`
2. Edita `.env` con tus credenciales locales (BD, correo, IA, etc.).

> **Importante**: el archivo `.env` está ignorado por git. Nunca subas secretos
> (claves de API, App Passwords, tokens, contraseñas) al repositorio. En
> producción `SECRET_KEY` debe ser aleatoria y `DEBUG=False`; la app **no**
> arranca en producción sin una `SECRET_KEY` real (falla con mensaje claro).

Ver todas las variables en el repositorio raíz (README) y en `backend/.env.example`.

## Migraciones, base de datos y ejecución
```bash
python manage.py migrate
python manage.py runserver
```

### Grafo de migraciones (normalizado)
- **core** quedó lineal sin volver a numerar nada: dos ramas históricas que
  partían de `core/0009` (rama del slug de `Empresa`.
  `0010_empresa_slug → 0011_backfill → 0012_no_nulo → 0013_venta_numero_factura`;
  rama de `0010_alter_carrito_...`) se concilian con la migración de **merge**
  `core/0014_merge_ramas_0010_slug_y_0010_carrito` (vacía, solo topología).
  La rama B conserva su nombre `0010_...` (así está aplicada en producción:
  **nunca se renombran migraciones ya aplicadas**) pero ahora apunta a su padre
  real `core/0009` en vez de a `0013`.
- **cuentas** es lineal (`0001 → ... → 0009`); su última migración depende
  de la rama B de core (hoja `0010_alter_carrito_...`), como corresponde a un
  grafo resuelto con merge.

### Procedimiento seguro para bases de datos existentes
1. **Backup** antes de tocar nada (migrar puede ejecutar DDL, no hay marcha
   atrás automática):
   - MySQL: `mysqldump --no-tablespaces -u USUARIO -p BASE > base-$(Get-Date -Format yyyyMMddHHmmss).sql`
   - O una snapshot/restore del servidor si está gestionado.
2. Revisa qué va a ejecutarse **sin** ejecutarlo:
   `python manage.py migrate --plan`
3. Aplica: `python manage.py migrate`.
4. Verifica coherencia y ausencia de modelos desincronizados:
   `python manage.py makemigrations --check --dry-run` (debe decir "No changes detected")
5. Reglas invariantes:
   - **No borres ni renombres** archivos de migración ya aplicados (la tabla
     `django_migrations` los referencia por app+nombre).
   - No edites a mano `django_migrations` ni uses `--fake` a la ligera; solo en
     procedimientos controlados y documentados.
   - Para revertir un cambio puntual usa `migrate <app> <migracion-anterior>`
     y reaplica; si una migración aplicada falla sobre una BD con datos, corrige
     los datos o la migración y vuelve a intentar (Django conoce el estado real).

### Instalación limpia
1. Crea la base y credenciales (ver `.env`): `CREATE DATABASE intersoft CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci;`
2. `python manage.py migrate` (aplica todo el grafo, incluido el merge `0014`
   y los seed de roles en `cuentas/0003_seed_rbac`).
3. Opcional: `python manage.py seed_demo` para datos de demostración.
4. `python manage.py runserver`.

Una instalación limpia y una base actualizada deben terminar con **el mismo
esquema**: el merge es vacío y los índices añadidos en `core/0015` son aditivos
(no cambian el modelo). La suite de pruebas (`python manage.py test`) crea una
base nueva en cada corrida, así que su verde garantiza que el grafo completo
funciona desde cero.

## Estructura
- **core/**: Lógica principal de la aplicación.
- **cuentas/**: Manejo de cuentas de usuario y autenticación (`/api/auth/*`).
- **intersoft/**: Proyecto Django (settings, urls del proyecto).
- **templates/**: Plantillas HTML para generar respuestas.

## Pruebas
```bash
python manage.py test
```
Requiere una base MySQL local accesible (ver `settings.py`); Django crea y
destruye una base de prueba automáticamente. Las pruebas de configuración
crítica viven en `backend/intersoft/tests.py`.

## Integración continua
El pipeline `.github/workflows/ci.yml` ejecuta sobre MySQL 8 (servicio de
GitHub Actions) y Python 3.12 con `DEBUG=False`:

1. `python manage.py check` — sin issues.
2. `python manage.py makemigrations --check --dry-run` — sin migraciones pendientes.
3. `python manage.py migrate` — instalación limpia (incluye el merge y seeds).
4. `python manage.py test` — suite completa.

## Calidad del backend (fase 5)
Refuerza la solidez del API sin cambiar contratos públicos de las fases 1-4.

### Verificación (comandos)
```bash
python manage.py check                 # sin issues
python manage.py makemigrations --check   # "No changes detected"
python manage.py test                  # suite completa
```

### Métricas de pruebas
- **241 tests** en verde (aumento desde 205 de la fase 4; +36 nuevas pruebas
  de la fase 5 que cierran los huecos de cobertura).
- Distribución por fichero de pruebas:
  - `core/tests_fase5.py` (nuevo, 26): forma de errores, filtros de consulta,
    validación de cámaras, paginación acotada, anulación, doble facturación y
    **carreras de concurrencia** (ventas POS sin oversell y checkout seriado).
  - `cuentas/tests.py` (+10): `/api/auth/me`, refresh, token inválido/expirado,
    password reset con token expirado/inexistente, shapes 400/403/404.
  - Resto: `core/tests.py`, `core/tests_aislamiento.py` (multiempresa),
    `core/tests_empleados.py` y `cuentas/tests.py`.

### Correcciones aplicadas
- **Errores uniformes**: `raise_exception=True` reemplazado en
  `cuentas/views.py` (login, cambiar-password, solicitar-recuperación) para
  devolver siempre el shape `{codigo, detalle, errores}` con su código; el
  manejador global (`core/exceptions.py`) no devuelve trazas ni datos sensibles.
- **Validación de entradas en consultas** (devuelven 400 uniforme):
  fechas `YYYY-MM-DD` en `ventas` y en `FiltrosDashboard` (dashboard y
  reportes, además de `categoria` como UUID), `precio_min`/`precio_max` y
  `categoria` en el catálogo público.
- **Validación de `url_stream`** de cámaras: solo `http(s)`, `rtsp`, `rtmp`;
  vacío se permite (cámara sin video). Bloquea valores como `javascript:`.
- **Paginación acotada**: Productos, Usuarios, MisPedidos e InventarioProductos
  devuelven como máximo 200 filas (parámetro `limite`, por defecto 50); antes
  devolvían listados sin tope.
- **Condiciones de carrera corregidas**:
  - `VentaPOSView`: un único `transaction.atomic()` — lock de producto +
    chequeo de stock + descuento + movimiento se mantienen hasta el commit
    (antes dos `atomic()` separados permitían oversell).
  - `ajuste_manual`: el `select_for_update` ahora está **dentro** del `atomic`
    (antes el lock se perdía al salir del bloque).
  - Correlativo `numero_factura`: la fila de `Empresa` se bloquea con
    `select_for_update` en POS y checkout para serializar el consecutivo.
  - Anulación: la venta y los productos se bloquean dentro de la transacción
    (antes los locks quedaban fuera del `atomic`).
  - Carrito/checkout: el carrito (y productos) se bloquean con `select_for_update`
    para serializar operaciones concurrentes del mismo comprador; `metodo_pago`
    se valida contra las opciones de `Venta`.
  - Facturación: la venta se bloquea para evitar doble `FacturaElectronica` y el
    `IntegrityError` (OneToOne) queda como respaldo devolviendo `YA_FACTURADA`.
  - Nota crédito: la venta se bloquea y todo el flujo (crear + enviar + revertir
    stock) es atómico.

### Endpoints verificados en la fase 5 (status + shape invariante)
- Autenticación: `POST /api/auth/login`, `POST /api/auth/refresh`,
  `GET /api/auth/me`, `POST /api/auth/cambiar-password/`,
  `POST /api/auth/password-reset/`, `POST /api/auth/password-reset/confirmar/`.
- Ventas/inventario: `POST /api/ventas/pos/`, `POST /api/ventas/<id>/anular/`,
  `GET /api/ventas/`, `POST /api/inventario/<id>/ajustar/`,
  `GET /api/inventario/productos/`, `GET /api/seguridad/usuarios/`.
- Tienda: `GET /api/tienda/catalogo/`, `POST /api/tienda/carrito/items/`,
  `PUT /api/tienda/carrito/items/<id>/`, `POST /api/tienda/checkout/`,
  `GET /api/tienda/pedidos/`.
- Facturación: `POST /api/facturacion/` (doble llamada → `YA_FACTURADA`),
  `POST /api/notas-credito/`.
- Dashboard/reportes: `GET /api/dashboard/resumen|ventas|top-productos|clientes-frecuentes`,
  `GET /api/reportes/vista|exportar` (filtros de fecha/categoría invalidados → 400).
- Monitoreo: `GET/POST /api/camaras/`, `PATCH /api/camaras/<id>/` (validación
  de `url_stream`).

Los test de concurrencia (`ConcurrenciaPOS`, `ConcurrenciaCheckout`) usan
`TransactionTestCase` + threads sobre MySQL: confirman que el servidor **no
sobrevende** stock ni ejecuta dos checkouts sobre el mismo carrito.
