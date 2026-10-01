# AGENTS.md — Contrato de OpenCode (agente único)

Proyecto: **intersoft-prueba_tecnica** (Django REST + MySQL 8 + Angular SPA,
multi-tenant). OpenCode lee este contrato al arrancar en este repo
(convención `AGENTS.md`) y lo cumple en cada sesión.

> Cambio de modelo (2026-10-01): antes había una orquestación Claude
> (supervisor) + OpenCode (ejecutor). A partir de ahora **no hay rol de
> supervisor separado**: OpenCode es el único agente y opera de forma
> autónoma (especifica, implementa, gatea y mergea él mismo). El humano del
> equipo es el dueño del producto y consultor, no un gate de código entre
> ramas.

---

## 1. Rol de OpenCode

| Aspecto | Qué hace | Qué NO hace |
|---|---|---|
| **OpenCode** | Define el detalle de la tarea a partir del requerimiento del humano, escribe código, corre tests/lint/migraciones localmente, abre commits en rama de trabajo, corre los gates de la sección 4 y **mergea a `main` cuando el CI está verde** | No toca `main` con código no verificado; no despliega a producción sin el paso operativo de la sección 4/DESPLIEGUE; no viola las invariantes de la sección 3 |

OpenCode puede operar sin pedir aprobación intermedia en el flujo normal
(crear rama, commitear, pushear, abrir PR, mergear cuando el CI está verde).
Las únicas operaciones que quedan a decisión humana explícita son las de la
sección 7 (despliegue a producción, habilitar integraciones reales o
comandos destructivos).

---

## 1.1 Consulta obligatoria del vault (todas las sesiones)

OpenCode lee `docs/INDICE.md` (MOC del repo) y `vault/INDICE.md` (índice de
notas del proyecto) antes de cada tarea y después de un merge relevante.
Reglas:

- Si una nota del vault contradice el plan de una tarea, OpenCode lo declara
  en su reporte y lo resuelve documentando la decisión (no lo ignora en
  silencio).
- Decisiones nuevas del trabajo se registran en `vault/decisiones.md` (con la
  plantilla `vault/plantillas/decision-nueva.md`), no solo en el commit.
- `vault/auditoria-bugs-opencode.md` es el registro de bugs reales de OpenCode
  y su estado; cualquier bug confirmado nuevo se agrega ahí antes del fix.
- Lo que vive en `.obsidian/` (config local del vault) **no** se lee ni se
  edita: para los agentes no existe; solo cuentan los archivos versionados.

---

## 2. Flujo por tarea

1. **Origen de la tarea**: el humano plantea el requerimiento (objetivo,
   archivos/módulos tocados, criterios de aceptación medibles, e invariantes
   que no se pueden romper de la sección 3). También puede venir de un ítem
   de `docs/ROADMAP.md` o un bug de `vault/auditoria-bugs-opencode.md`.
2. **OpenCode implementa** en una rama nueva desde `main` (`feature/<slug>`
   o `fix/<slug>`), corriendo localmente los mismos chequeos que el CI
   (sección 4) antes de pushear.
3. **OpenCode reporta** en el PR: diff, resultado de tests/lint, y cualquier
   desviación del plan original (si tuvo que tocar algo fuera de lo
   especificado, lo declara explícito, no lo hace silencioso).
4. **Merge**: OpenCode abre el PR, espera a que el CI quede verde y mergea a
   `main` con squash. No hay revisión humana previa obligatoria al merge;
   el humano puede revisar el PR después de mergeado y pedir correcciones
   (se aplican en rama nueva).
5. **Nada de cambios masivos automáticos**: un PR/tarea toca un módulo
   acotado. Refactors amplios (tocar `core/` completo, cambiar ORM,
   actualizar Angular major) se parten en pasos chicos revisables, nunca
   una tarea única gigante.

---

## 3. Invariantes que no se pueden romper

Tomadas de `README.md`, `docs/RIESGOS.md`, `docs/CHECKLIST-SEGURIDAD.md`,
`docs/DESPLIEGUE.md`. OpenCode no puede introducir un cambio que las viole;
si una tarea lo requiere, es decisión del humano del equipo explícita,
documentada en el commit.

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
  integración siempre pasan por revisión manual del humano antes de merge.
- **Migraciones**: nunca se edita una migración ya aplicada en `main`;
  siempre migración nueva. `python manage.py makemigrations --check --dry-run`
  debe devolver "No changes detected" antes de commit.
- **Secretos**: `.env` real nunca se versiona; nada de credenciales
  (`SECRET_KEY`, `DB_PASSWORD`, `IA_API_KEY`, `WA_TOKEN`, `DIAN_*`) en código,
  logs o mensajes de commit.
- **Contratos de API**: no se cambia forma de respuesta de un endpoint
  existente (`{codigo, detalle, errores}` en errores). Si un cambio lo
  amerita, se declara como breaking change y se actualiza el frontend en la
  misma tarea.

---

## 4. Gates de calidad obligatorios (antes de que OpenCode mergee)

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
mergear, no mergea "con fallas conocidas" (salvo excepción explícita
marcada por el humano, p. ej. un `npm audit` previo ajeno a la rama,
documentada en el PR).

---

## 5. Estrategia de actualización automatizada (mejorar sin romper)

Objetivo: dejar que OpenCode itere sobre el código (refactors, fixes,
mejoras del `docs/ROADMAP.md`) de forma continua, sin que un cambio malo
llegue a producción.

1. **Alcance por tarea, no por sesión libre.** OpenCode nunca ejecuta "mejora
   lo que veas" sin una tarea concreta del humano (evita scope creep y
   cambios no auditables). Cada tarea = un ítem del roadmap o un pedido
   explícito.
2. **Rama aislada + commits atómicos.** Una tarea, una rama, commits
   pequeños con mensaje Conventional Commits (`fix:`, `feat:`, `refactor:`,
   `chore:`). Facilita revert quirúrgico si algo falla después.
3. **Ningún cambio sin tests que lo cubran.** Si la tarea toca lógica de
   negocio (`core/models.py`, `services/`, `analytics.py`), agrega o ajusta
   test antes de mergear. Cobertura no puede bajar de 70% (gate ya en CI).
4. **Gate antes de `main`:** CI verde (automático) + verificación local de
   invariantes de la sección 3. El CI es el gate que decide el merge.
5. **Cambios reversibles primero.** Preferir flags/config sobre reescritura
   irreversible: el proyecto ya usa el patrón (`DIAN_MOCK`, `IA_PROVIDER`,
   `WA_VINCULADO`). Una mejora nueva que cambie comportamiento observable
   entra detrás de un flag apagado por defecto hasta validarse en staging.
6. **Migraciones de DB con plan de reversa.** Antes de aplicar en un entorno
   con datos reales: `migrate --plan`, backup, y confirmar que
   `migrate <app> <migración_anterior>` funciona en local.
7. **Nada de cambios masivos automáticos.** Un PR/tarea toca un módulo
   acotado. Refactors amplios se parten en pasos chicos revisables.
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

### 6.2. Frontend (ya implementado — commit `6c0d6a3`)

Panel y seguimiento de Envíos terminados y probados:

1. `frontend/src/app/core/models/tienda.model.ts`: tipos `Envio`/`EnvioSeguimiento`,
   `ENVIO_ESTADOS` y `ENVIO_TRANSICIONES`; `Pedido` ya incluye `envio`.
2. `frontend/src/app/core/services/envios.service.ts` (personal interno):
   `listarEnvios(estado?)`, `obtenerEnvio(ventaId)`, `actualizarEnvio(ventaId,
   datos)` contra `/api/envios/` y `/api/ventas/<id>/envio/`. El comprador
   sigue viendo el envío dentro de su `Pedido` (sin endpoint aparte).
3. `frontend/src/app/features/tienda/pedidos/`: seguimiento de despacho
   (`estado_display`, transportadora, guía, fecha estimada, dirección) en
   cada pedido con envío.
4. `frontend/src/app/features/envios/` (ruta `/envios`, `personalGuard`,
   enlace en el sidebar): cola filtrable por estado + modal para cambiar
   transportadora/guía/fecha/notas/estado (solo transiciones válidas).
5. Tests: Vitest (`envios.component.spec.ts`, `envios.service.spec.ts`,
   `pedidos`/`sidebar`) + e2e Playwright (`frontend/e2e/tienda-flujo.spec.ts`,
   cubre el panel `/envios`).

Gate superado: `npm run lint`, `npm run build`, `npm run test:ci` (63/63) en
la sesión de cierre del módulo.

---

## 7. Qué puede hacer OpenCode sin pedir aprobación

**Sin aprobación previa** (operación normal, dentro de una tarea):
- Leer, editar, crear archivos dentro de `backend/`, `frontend/`, `docs/`,
  `vault/`.
- Correr tests, lint, migraciones locales, `npm`/`pip` en modo lectura
  (install de deps ya pinneadas en lockfile/requirements).
- Commits en su rama de trabajo, push de la rama, apertura y **merge del PR
  a `main` cuando el CI está verde**.

**Requiere aprobación explícita del humano antes de ejecutar:**
- Cualquier comando de despliegue a producción (docker-compose contra un
  host remoto, pasos de `docs/DESPLIEGUE.md` fuera de un entorno local).
- Cambiar `DIAN_MOCK`, `IA_PROVIDER`, o cualquier variable de
  `backend/.env.example` que afecte producción (integración real con
  credenciales).
- Borrar o editar una migración ya commiteada en `main`.
- Instalar una dependencia nueva no pinneada (cambia `requirements.txt` /
  `package.json` con paquete no discutido).
- Cualquier comando destructivo (`DROP`, `migrate zero`, `rm -rf`, reset de
  BD) fuera de un entorno de test local descartable.

---

## 8. Convención de ramas y commits

- Ramas: `feature/<slug>`, `fix/<slug>`, `refactor/<slug>`, `chore/<slug>`
  desde `main`.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`,
  `docs:`, `chore:`), en español o inglés consistente con el resto del repo
  (el repo actual mezcla, mantener lo que ya exista en el archivo tocado).
- Un PR = una tarea de la sección 2. PRs grandes que agrupan varias tareas no
  se aceptan (dificulta revert y revisión).
- Tras el merge, cuando corresponda, actualizar el registro vivo:
  `vault/ACTUALIDAD.md`, la sección de riesgos resueltos de
  `docs/RIESGOS.md` o `docs/PR-BODY-<n>.md`, como ya hace el repo.