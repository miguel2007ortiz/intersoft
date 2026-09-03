# AGENTS.md — Orquestación Claude (supervisor) + OpenCode (ejecutor)

Proyecto: **intersoft-prueba_tecnica** (Django REST + MySQL 8 + Angular SPA,
multi-tenant). Este archivo es el contrato único que leen ambos agentes antes
de tocar código. OpenCode lee este archivo automáticamente al arrancar en
este repo (convención `AGENTS.md`); Claude lo usa como referencia de
supervisión en cada sesión.

---

## 1. Roles (no se mezclan)

| Rol | Quién | Qué hace | Qué NO hace |
|---|---|---|---|
| **Supervisor** | Claude (esta sesión/CLI, en la nube o en el equipo del dev) | Define requerimientos, diseño, contratos de API, criterios de aceptación; revisa diffs antes de merge; decide si algo rompe una invariante de `docs/RIESGOS.md` o `docs/CHECKLIST-SEGURIDAD.md` | No ejecuta comandos de escritura en el repo local del dev, no corre `git push`, no despliega |
| **Ejecutor** | OpenCode (CLI local, máquina del dev) | Escribe código, corre tests/lint/migraciones localmente, abre commits en rama de trabajo, reporta resultado | No decide alcance ni arquitectura por su cuenta; no mergea a `main`/`develop`; no despliega a producción sin gate de Claude |

Ninguno de los dos agentes empuja directo a `main`/`develop` ni dispara
despliegue a producción sin pasar los gates de la sección 4.

---

## 2. Flujo por tarea

1. **Claude especifica** la tarea: objetivo, archivos/módulos tocados
   (`backend/core`, `backend/cuentas`, `frontend/src/...`), criterios de
   aceptación medibles (tests que deben pasar, endpoint que debe responder
   X), e invariantes que no se pueden romper (tabla de la sección 3).
2. **OpenCode implementa** en una rama nueva desde `develop`
   (`feature/<slug>` o `fix/<slug>`), corriendo localmente los mismos
   chequeos que el CI (sección 4) antes de reportar terminado.
3. **OpenCode reporta**: diff, resultado de tests/lint, y cualquier
   desviación del plan original (si tuvo que tocar algo fuera de lo
   especificado, lo declara explícito, no lo hace silencioso).
4. **Claude revisa** el diff contra el criterio de aceptación y las
   invariantes. Devuelve: aprobado → merge a `develop`; o cambios
   solicitados → vuelve a paso 2.
5. **Merge a `main`** solo desde `develop` verde en CI (`.github/workflows/ci.yml`),
   nunca directo desde una rama de feature.
6. **Despliegue** vía enviso (sección 6) solo después de merge a `main` con
   CI verde.

---

## 3. Invariantes que no se pueden romper

Tomadas de `README.md`, `docs/RIESGOS.md`, `docs/CHECKLIST-SEGURIDAD.md`,
`docs/DESPLIEGUE.md`. OpenCode no puede introducir un cambio que las viole;
si una tarea lo requiere, es decisión de Claude explícita, documentada en el
commit.

- **Seguridad de arranque**: con `DEBUG=False` la app falla al arrancar si
  `SECRET_KEY` es placeholder/ausente o `ALLOWED_HOSTS` incluye `*`.
  `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS y
  `X_FRAME_OPTIONS=DENY` se mantienen activos en producción.
- **Multi-tenant**: todo query nuevo sobre modelos con FK a `Empresa` filtra
  por tenant. No se agregan endpoints ni vistas que crucen datos entre
  empresas sin permiso explícito.
- **Dinero/stock**: operaciones sobre `Venta`/`DetalleVenta`/inventario usan
  `select_for_update` (evitar condiciones de carrera); `Venta.total` debe
  seguir siendo consistente con la suma de `DetalleVenta.subtotal`.
  DIAN (`services/dian_adapter.py`) permanece con `DIAN_MOCK=True` por
  defecto salvo tarea explícita de habilitación real con credenciales.
  DIAN real: **fuera de la actualización automática** — cambios a esa
  integración siempre pasan por revisión manual (Claude no aprueba merge
  automático).
- **Migraciones**: nunca se edita una migración ya aplicada en `develop`/`main`;
  siempre migración nueva. `python manage.py makemigrations --check --dry-run`
  debe devolver "No changes detected" antes de commit.
- **Secretos**: `.env` real nunca se versiona; nada de credenciales
  (`SECRET_KEY`, `DB_PASSWORD`, `IA_API_KEY`, `WA_TOKEN`, `DIAN_*`) en código,
  logs o mensajes de commit.
- **Contratos de API**: no se cambia forma de respuesta de un endpoint
  existente (`{codigo, detalle, errores}` en errores) sin que Claude lo
  marque como breaking change y actualice el frontend en la misma tarea.

---

## 4. Gates de calidad obligatorios (antes de que OpenCode reporte "listo")

Estos son los mismos pasos que corre `.github/workflows/ci.yml` — correrlos
local evita que CI rebote la rama.

**Backend** (`cd backend`, venv activo):
```bash
ruff check .
bandit -c bandit.yaml -r .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
coverage run manage.py test core && coverage report --fail-under=70
```

**Frontend** (`cd frontend`):
```bash
npm run lint
npm run build
npm run test:ci
```

Si cualquiera falla, la tarea no está lista — OpenCode corrige antes de
reportar a Claude, no reporta "terminado con fallas conocidas".

---

## 5. Estrategia de actualización automatizada (mejorar sin romper)

Objetivo: dejar que OpenCode itere sobre el código (refactors, fixes,
mejoras del `docs/ROADMAP.md`) de forma continua, sin que un cambio malo
llegue a producción.

1. **Alcance por tarea, no por sesión libre.** OpenCode nunca ejecuta "mejora
   lo que veas" sin una tarea concreta de Claude (evita scope creep y
   cambios no auditables). Cada tarea = un ítem del roadmap o un pedido
   explícito.
2. **Rama aislada + commits atómicos.** Una tarea, una rama, commits
   pequeños con mensaje Conventional Commits (`fix:`, `feat:`, `refactor:`,
   `chore:`). Facilita revert quirúrgico si algo falla después.
3. **Ningún cambio sin tests que lo cubran.** Si la tarea toca lógica de
   negocio (`core/models.py`, `services/`, `analytics.py`), agrega o ajusta
   test antes de reportar. Cobertura no puede bajar de 70% (gate ya en CI).
4. **Doble gate antes de `main`:** CI verde (automático) + revisión de
   Claude (diseño/lógica/invariantes, sección 3) — ninguno sustituye al otro.
5. **Cambios reversibles primero.** Preferir flags/config sobre reescritura
   irreversible: el proyecto ya usa el patrón (`DIAN_MOCK`, `IA_PROVIDER`,
   `WA_VINCULADO`). Una mejora nueva que cambie comportamiento observable
   entra detrás de un flag apagado por defecto hasta validarse en staging.
6. **Migraciones de DB con plan de reversa.** Antes de aplicar en un entorno
   con datos reales: `migrate --plan`, backup, y confirmar que
   `migrate <app> <migración_anterior>` funciona en local.
7. **Nada de cambios masivos automáticos.** Un PR/tarea toca un módulo
   acotado. Refactors amplios (tocar `core/` completo, cambiar ORM,
   actualizar Angular major) se parten en pasos chicos revisables, nunca
   una tarea única gigante.
8. **Registro de decisiones.** Cambios de arquitectura o que tocan una
   invariante de la sección 3 se anotan en `docs/RIESGOS.md` o
   `docs/ROADMAP.md` (igual que ya se hace ahí), no solo en el commit.

---

## 6. Módulo de Envíos (despachos/logística del marketplace)

> Corrección: no existe una herramienta externa "enviso". Es el módulo de
> **Envíos** (despachos) de las ventas del marketplace de este mismo
> proyecto — hasta ahora inexistente en el código (`Venta` no tenía ningún
> campo de logística; `direccion`/`ciudad` solo vivían en `Cliente`, sin
> snapshot por pedido ni estado de despacho). El despliegue real del
> proyecto sigue siendo el manual de `docs/DESPLIEGUE.md` (gunicorn + nginx),
> sin cambios — no hay una sección de "deploy automatizado" que reemplazar.

### 6.1. Diseño (ya implementado en esta sesión)

- **Modelo `Envio`** (`backend/core/models.py`, migración `0018_envio.py`):
  1:1 con `Venta`, solo para ventas del canal marketplace (las crea
  `CheckoutView`; una venta de mostrador/POS no tiene `Envio`).
  Snapshot de `direccion`/`ciudad` del cliente al momento de la compra
  (igual criterio que `numero_factura`/`precio_unitario`: dato histórico
  que no cambia si el cliente edita su perfil después).
- **Máquina de estados** (`Envio.cambiar_estado`, `TRANSICIONES_VALIDAS`):
  `pendiente → preparando → despachado → en_transito → entregado`, con
  `no_entregado` como reintento (`no_entregado → en_transito | devuelto`).
  `entregado`/`devuelto` son terminales. Transición no listada = rechazada
  (`TRANSICION_INVALIDA`, 400), nunca se aplica un estado arbitrario.
- **Checkout ahora exige dirección de envío**: `CheckoutView` rechaza con
  `SIN_DIRECCION_ENVIO` (400) si `cliente.direccion`/`cliente.ciudad` están
  vacías, antes de tocar stock — evita crear un envío sin destino. Mismo
  patrón que el ya existente `SIN_CLIENTE`.
- **API para personal interno** (`EsPersonal`, aislado por empresa vía
  `_obtener_empresa`, con `select_for_update` en la escritura — mismo
  patrón que `VentaDetalleView.anular`):
  - `GET /api/envios/?estado=<estado>` — cola de trabajo, ordenada por
    antigüedad.
  - `GET /api/ventas/<id>/envio/` — detalle.
  - `PATCH /api/ventas/<id>/envio/` — actualiza `transportadora`,
    `numero_guia`, `fecha_entrega_estimada`, `notas` y/o `estado`.
- **API para el comprador**: `GET /api/tienda/pedidos/` ahora incluye
  `envio` (subset de seguimiento, sin `notas` internas del vendedor) en
  cada pedido — `null` si la venta no tiene envío (ventas previas a esta
  funcionalidad).
- **Tests**: `core/tests.py` clase `EnvioCreacionTest`/`EnvioGestionTest`
  (creación en checkout, rechazo sin dirección, transición inválida,
  aislamiento multi-tenant, filtro de lista). Fixtures de
  `BaseMarketplaceTest`/`ConcurrenciaCheckout` actualizadas con
  `direccion`/`ciudad` (si no, el nuevo `SIN_DIRECCION_ENVIO` las habría
  roto). Suite completa: 243/243 verde, `ruff`/`bandit` limpios, cobertura
  86% (gate 70%).

### 6.2. Tarea abierta para OpenCode (frontend — próxima tarea, no bloqueante)

El backend queda completo y probado; falta la parte visual. Alcance de UNA
tarea (sección 2 de este archivo), no varias mezcladas:

1. `frontend/src/app/core/models/tienda.model.ts`: agregar tipo `Envio`
   (campos de `EnvioSeguimientoSerializer`) y anexarlo a `Pedido`.
2. `frontend/src/app/core/services/tienda.service.ts`: el `envio` ya viaja
   dentro de `Pedido` (no requiere endpoint nuevo del lado comprador).
3. `frontend/src/app/features/tienda/pedidos/`: mostrar estado de envío
   (`estado_display`, transportadora, número de guía, fecha estimada) en
   cada pedido del historial del comprador.
4. Servicio nuevo o extensión de un servicio de ventas ya existente:
   `listarEnvios(estado?)`, `obtenerEnvio(ventaId)`,
   `actualizarEnvio(ventaId, datos)` contra `/api/envios/` y
   `/api/ventas/<id>/envio/`.
5. `frontend/src/app/features/ventas/` (o una carpeta `envios/` nueva junto
   a ella, mismo nivel que `alertas/`/`inventario/`): panel para personal
   interno — lista filtrable por estado, acción para cambiar
   transportadora/guía/estado. Reusar el patrón visual ya usado en
   `features/alertas`.
6. Tests: Vitest para el componente nuevo + el server ya cubierto por
   backend (no duplicar ahí).

Gate de esta tarea: sección 4 de este archivo (`npm run lint`,
`npm run build`, `npm run test:ci`) antes de reportar terminado.

---

## 7. Qué puede hacer OpenCode sin pedir aprobación

**Sin aprobación previa** (dentro de una tarea ya especificada por Claude):
- Leer, editar, crear archivos dentro de `backend/`, `frontend/`, `docs/`.
- Correr tests, lint, migraciones locales, `npm`/`pip` en modo lectura
  (install de deps ya pinneadas en lockfile/requirements).
- Commits en su rama de trabajo.

**Requiere aprobación explícita de Claude antes de ejecutar:**
- `git push` a `main`/`develop`, merge de PR.
- Cualquier comando de despliegue (enviso, docker-compose contra un host
  remoto).
- Cambiar `DIAN_MOCK`, `IA_PROVIDER`, o cualquier variable de
  `backend/.env.example` que afecte producción.
- Borrar o editar una migración ya commiteada en `develop`/`main`.
- Instalar una dependencia nueva no pinneada (cambia `requirements.txt` /
  `package.json` con paquete no discutido).
- Cualquier comando destructivo (`DROP`, `migrate zero`, `rm -rf`, reset de
  BD) fuera de un entorno de test local descartable.

---

## 8. Convención de ramas y commits

- Ramas: `feature/<slug>`, `fix/<slug>`, `refactor/<slug>`, `chore/<slug>`
  desde `develop`.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`,
  `docs:`, `chore:`), en español o inglés consistente con el resto del repo
  (el repo actual mezcla, mantener lo que ya exista en el archivo tocado).
- Un PR = una tarea de la sección 2. PRs grandes que agrupan varias tareas no
  se aceptan (dificulta revert y revisión).
