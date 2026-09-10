---
titulo: "Auditoría de bugs backend + plan de prompts para OpenCode"
fecha: 2026-09-10
estado: hallazgos 1-6 corregidos directamente por Claude (sin pasar por OpenCode);
  7-13 siguen pendientes
relacionado: [docs/RIESGOS.md, AGENTS.md]
---

**Nota (2026-09-10):** el plan de prompts de más abajo se escribió para
ejecutarse con OpenCode, pero el usuario pidió arreglar los bugs
directamente en esta sesión. Los hallazgos #1, #2, #3, #4, #5 y #6 ya están
corregidos, con test de regresión y commit atómico en `intersoft_miguel`:

- #1 (XSS `exportar_html`) + #11 (CSV injection): `commit 75dbc90` (sesión previa).
- #2 (DIAN dentro de lock) + #3 (`IntegrityError` nota crédito): `commit 17c1d0a` (sesión previa).
- #4 (RBAC hardcodeado): `commit f03b3b5`.
- #5 (pasarela cobra antes de reservar stock) + #6 (carrera en `_carrito_de`): `commit fcc873f`.

Quedan pendientes: #7, #8, #9, #10, #12, #13 (ver plan de Fase 2 de más abajo
para #9/#10 vía "2E"; #7, #8, #12, #13 no tienen bloque de prompt propio
todavía). El plan de Fase 1/3/4 de OpenCode de más abajo queda como
referencia histórica, no se ejecutó.

# Auditoría de bugs — InterSoft (backend)

Nota de trabajo del vault: hallazgos reales, leídos directamente en código
(`backend/core/`, `backend/cuentas/`), no supuestos. Cuando un fix se aplique,
promover la entrada correspondiente a `docs/RIESGOS.md` (sección resueltos) y
marcar aquí como hecho.

## Hallazgos y severidad

| # | Sev | Archivo:línea | Bug real |
|---|---|---|---|
| 1 | 🔴 | `core/analytics.py` `exportar_html` | Interpola `producto`, `sku`, `categoria`, `cliente`, `empresa.nombre` en HTML con f-string sin escapar → XSS almacenado al exportar/imprimir un reporte con nombre malicioso. |
| 2 | 🔴 | `core/views_facturacion.py` (`FacturasView.generar`, `NotasCreditoView.crear`) + `services/dian_adapter.py` (`ClienteDIANReal._cliente`) | Llamada SOAP a la DIAN dentro de `transaction.atomic()` con `select_for_update()` sobre la venta, y sin `timeout` en el `Transport` de zeep. `FacturaReintentarView` sí llama fuera del atomic — patrón correcto existe pero no se aplica en todos lados. |
| 3 | 🔴 | `core/views_facturacion.py` (`NotasCreditoView.crear`) | `NotaCredito.objects.create()` sin `try/except IntegrityError`; reintentar tras estado `rechazada` puede violar `unique=True` de `numero` → 500 en vez de error de dominio. |
| 4 | 🟠 | `cuentas/permissions.py` (`EsAdministrador`, `EsPersonal`) | Gatean por `perfil.rol.nombre` literal en vez de `TienePermiso(codigo)`; ignoran roles personalizados por empresa y no protegen contra `perfil.rol is None` (→ 500). |
| 5 | 🟠 | `core/views_tienda.py` (`CheckoutView.post`) | La pasarela de pago se resuelve antes de `transaction.atomic()`; si el stock falla dentro, no hay reverso del cobro. Inocuo hoy por `PASARELA_MOCK=True`. |
| 6 | 🟠 | `core/views_tienda.py` (`_carrito_de`) | `Carrito.objects.create()` fuera de lock cuando el usuario no tiene carrito → carrera posible sobre el `OneToOneField`. |
| 7 | 🟠 | `core/signals.py` (`mantener_totales_venta`) vs vistas de venta | Doble fuente de verdad: la vista calcula y guarda `subtotal`/`total`; el signal los recalcula y sobrescribe en cada línea. La validación `descuento > subtotal` solo vive en la vista. |
| 8 | 🟠 | `core/views_ventas.py` (`VentasView.get`) | Estadísticas (`Sum('total')`) no filtran por `estado` salvo query param explícito → ingresos inflados con ventas anuladas/pendientes. |
| 9 | 🟠 | `core/exceptions.py` | El 500 no controlado devuelve `{'detail': ...}`, rompiendo el contrato `{codigo, detalle, errores}` que el resto de la API y el frontend dan por garantizado. |
| 10 | 🟢 | `core/views_ia.py` (respuesta `IA_NO_DISPONIBLE`) | El 502 de fallo de IA omite la clave `errores` del contrato estándar. |
| 11 | 🟢 | `core/analytics.py` (`exportar_csv`) | Sin mitigación de CSV/formula injection (celdas que empiezan con `= + - @`). |
| 12 | 🟢 | `core/models.py` (`_generar_numero_factura`) | Parámetro `bloqueada` muerto; `consecutivo` vía `COUNT(*)` por empresa; sin guard estructural fuera de las dos vistas que sí bloquean `Empresa`. |
| 13 | 🟢 | `frontend/package.json` (`lint`) | `npm run lint` = `prettier --check` sobre 4 archivos fijos; sin ESLint real. |

**Confirmado correcto (no tocar):** locks de POS/inventario/anulación
(`views_ventas.py`), aislamiento multi-tenant por `.filter(empresa=...)` en
todas las vistas revisadas, degradación limpia del asistente IA ante fallo del
proveedor real, módulo de cámaras con `disponible=False` explícito (ver
`docs/RIESGOS.md` §pendientes, punto 1 — coincide).

---

# Plan de prompts para OpenCode

Orden de ejecución: Fase 1 → Fase 2 (2A-2E, una corrida por fix) → Fase 3 → Fase 4.
Contexto compartido: OpenCode arranca con `AGENTS.md`/`docs/RIESGOS.md`/`opencode.json`
cargados; rama por tarea, commits atómicos, gates de `AGENTS.md` §4 antes de
reportar "listo", nunca tocar migraciones aplicadas, nunca `git push`/merge sin
aprobación.

## FASE 1 — Análisis y enfoque (sin tocar código)

```text
Actúa como ingeniero senior sobre este repo (Django REST + MySQL + Angular, ver AGENTS.md).
NO edites ningún archivo en esta tarea: solo lectura y validación.

Confirma o refuta, citando archivo:línea, cada uno de estos 6 hallazgos:

1. core/views_facturacion.py -> FacturasView.generar y NotasCreditoView.crear llaman al
   adaptador DIAN (services/dian_adapter.py) DENTRO de transaction.atomic() con
   select_for_update() sobre la venta; FacturaReintentarView llama FUERA. El Transport de
   zeep en ClienteDIANReal._cliente no tiene timeout configurado.
2. core/views_facturacion.py -> NotasCreditoView.crear: NotaCredito.objects.create() no
   captura IntegrityError; se permite reintentar tras estado 'rechazada' pero `numero` es
   unique=True global.
3. cuentas/permissions.py -> EsAdministrador/EsPersonal comparan perfil.rol.nombre en vez
   de usar TienePermiso(codigo); no hay guard si perfil.rol es None.
4. core/views_tienda.py -> CheckoutView.post: la pasarela de pago se resuelve ANTES de
   transaction.atomic(); si el stock falla dentro, no hay reverso del cobro.
5. core/signals.py -> mantener_totales_venta recalcula y sobrescribe Venta.subtotal/total
   que la vista ya había calculado; valida contra views_ventas.py y views_tienda.py.
6. core/exceptions.py -> manejador_excepciones: el 500 no controlado devuelve {'detail':...}
   en vez de {codigo, detalle, errores}.
7. core/analytics.py -> exportar_html: interpola producto/sku/categoria/cliente/empresa.nombre
   en HTML sin escapar (XSS almacenado).

Entrega:
A. Tabla final: hallazgo | CONFIRMADO/PARCIAL/REFUTADO | archivo:línea | severidad
   (Crítico/Medio/Bajo).
B. Para los 3 críticos (DIAN en lock, IntegrityError nota crédito, XSS en analytics):
   archivos exactos a tocar y el test existente (archivo::clase::método en
   backend/core/tests*.py) que lo cubre o debería cubrirlo.
C. Riesgos de regresión de cada fix contra las invariantes de AGENTS.md §3 (multi-tenant,
   locking de dinero/stock, contrato de error, migraciones).
NO propongas código del fix todavía. Solo el mapa de trabajo.
```

## FASE 2 — Refactorización quirúrgica (un archivo a la vez)

> Ejecutar una vez por fix, en orden 2A → 2B → 2C → 2D → 2E. Cada corrida
> carga solo los archivos listados en su bloque, no el repo completo.

```text
Tarea de fix único, alcance cerrado. Sigue AGENTS.md (rama fix/<slug> desde develop,
commits atómicos, Conventional Commits en español, sin tocar migraciones aplicadas).
Carga SOLO los archivos listados abajo. Muéstrame el diff propuesto antes de aplicarlo.

2A) fix/xss-reporte-html
  Archivos: core/analytics.py (exportar_html, _presentar, exportar_csv).
  - Escapar todo valor interpolado en el HTML con django.utils.html.escape/format_html.
  - En exportar_csv: prefijar con comilla simple cualquier celda que empiece por = + - @.
  - Test nuevo: producto con nombre "<script>alert(1)</script>" y "=CMD()" -> verificar
    que el HTML/CSV exportado los neutraliza.

2B) fix/nota-credito-integrityerror
  Archivo: core/views_facturacion.py (NotasCreditoView.crear).
  - Envolver NotaCredito.objects.create() en try/except IntegrityError -> 400 con
    {"codigo": "YA_TIENE_NOTA", "detalle": ..., "errores": null} (mismo patrón que
    FacturasView.generar).
  - Test: crear nota, forzar rechazo, reintentar -> debe dar 400 de dominio, no 500.

2C) fix/dian-fuera-de-transaccion
  Archivos: core/views_facturacion.py (FacturasView.generar, NotasCreditoView.crear),
  core/services/dian_adapter.py (ClienteDIANReal._cliente), backend/intersoft/settings.py.
  - Mover la llamada a la DIAN fuera de transaction.atomic() (patrón ya usado en
    FacturaReintentarView): crear el registro 'pendiente', commit, llamar sin lock,
    aplicar el resultado en una segunda transacción corta.
  - Añadir timeout al Transport de zeep vía settings.DIAN_TIMEOUT (default 20, leído de
    env, documentado en .env.example).
  - Mantener intacto: el reverso de stock de la nota crédito sigue atómico con
    select_for_update sobre los productos (invariante AGENTS.md §3).
  - Test: mockear una DIAN lenta y verificar que la fila de la venta no queda bloqueada
    durante la llamada.

2D) fix/rbac-permisos-finos
  Archivo: cuentas/permissions.py.
  - Sustituir la comparación por perfil.rol.nombre en EsAdministrador/EsPersonal por
    checks contra TienePermiso(codigo) donde exista el código de permiso equivalente;
    donde no exista, documenta cuál falta crear en Rol/Permiso.
  - Guard: si perfil.rol is None, denegar (403) en vez de lanzar AttributeError.
  - Test: rol personalizado con permiso equivalente debe pasar donde antes solo pasaba
    "ADMINISTRADOR"/"EMPLEADO" por nombre.

2E) fix/contrato-error-500
  Archivo: core/exceptions.py.
  - El fallback no controlado debe devolver {"codigo": "ERROR_INTERNO",
    "detalle": "Ocurrio un error inesperado. Intenta de nuevo en unos minutos.",
    "errores": null} con 500, sin perder el logger.exception.
  - Revisa frontend/src/app/core/utils/django-error.util.ts: confirma que ya parsea
    cuerpo['codigo']/['detalle']; ajústalo en la misma tarea si no.
  - Extra: core/views_ia.py, respuesta 502 de IA_NO_DISPONIBLE debe incluir
    "errores": null para uniformar el contrato.
  - Test: forzar una excepción no-DRF y assert de la forma nueva.

Al terminar cada fix: corre los gates de AGENTS.md §4 (ruff, bandit, check,
makemigrations --check --dry-run, test, coverage --fail-under=70). Reporta diff + salida
de gates. No avances al siguiente fix sin mi aprobación.
```

## FASE 3 — QA y pruebas nativas en terminal

```text
Verificación de las correcciones de la Fase 2. Ejecuta con "!" y pega la salida REAL
completa, sin resumir. Si algo falla, detente y repórtalo tal cual.

Backend (cd backend, venv activo):
  !ruff check .
  !bandit -c bandit.yaml -r .
  !python manage.py check
  !python manage.py makemigrations --check --dry-run
  !python manage.py test
  !coverage run manage.py test core && coverage report --fail-under=70

Frontend (cd frontend):
  !npm ci
  !npm run build
  !npm run test:ci

Confirma explícitamente el conteo: backend 241 tests, 0 failures, 0 errors;
frontend 20 tests (Vitest), 0 failures. Si el conteo no coincide, explica por qué
(tests nuevos de la Fase 2 cuentan a favor; cualquier test roto o eliminado sin
explicación es una alerta).

Extra:
  !python manage.py test core.tests_facturacion core.tests_dian
  !git log --oneline develop..HEAD
  !git diff --stat develop..HEAD

Entrega cuadro: [fix] | [gate backend] | [gate frontend] | [tests nuevos] | PASA/FALLA.
Si makemigrations detecta cambios, es un error de la Fase 2: identifícalo y dime cómo
revertir esa parte antes de seguir.
```

## FASE 4 — Reporte de entrega

```text
Genera la documentación final de esta ronda, en español, tono profesional. Usa
docs/DESPLIEGUE.md y docs/RIESGOS.md como base de formato y referencia cruzada.

1. docs/CAMBIOS-<fecha>.md (nuevo archivo):
   - Resumen ejecutivo (3-4 líneas).
   - Tabla: # | Severidad | Archivo(s) | Problema | Solución aplicada | Commit (hash) |
     Test que lo cubre.
   - Sección "Invariantes de AGENTS.md §3 verificadas".
   - Actualiza docs/RIESGOS.md: mueve cada riesgo resuelto de "pendientes" a "resueltos".
   - Si algo de docs/DESPLIEGUE.md queda afectado (ej. nueva variable DIAN_TIMEOUT en
     .env.example), documéntalo ahí también.
   - Pendientes explícitos: hallazgos 🟢 no abordados (CSV injection, numero_factura,
     lint cosmético del frontend) con recomendación breve.
   - Cómo revertir: `git revert <hash>` en orden inverso.

2. Cuerpo de Pull Request (imprímelo, no lo subas ni hagas push):
   - Título: "fix: correcciones críticas de auditoría (XSS reporte, DIAN fuera de
     transacción, RBAC fino, contrato de error, +N)"
   - Checklist de AGENTS.md §4 con el resultado real de la Fase 3.
   - Riesgos y plan de rollback.
   - Nota para el revisor: qué mirar primero (analytics.exportar_html y
     views_facturacion.py).

No hagas git push ni abras el PR: deja los commits en la rama y entrégame el cuerpo
para revisión.
```

## Seguimiento

- [ ] Fase 1 corrida y validada (no se ejecuto: se corrigio directo, ver nota arriba)
- [x] 2A xss-reporte-html — commit 75dbc90
- [x] 2B nota-credito-integrityerror — commit 17c1d0a
- [x] 2C dian-fuera-de-transaccion — commit 17c1d0a
- [x] 2D rbac-permisos-finos — commit f03b3b5
- [ ] 2E contrato-error-500 — pendiente
- [x] (fuera del plan original) checkout cobra tras reservar stock + carrera
      en _carrito_de — commit fcc873f
- [ ] Fase 3 (gates completos AGENTS.md §4) — corridos parcialmente:
      ruff + `python manage.py test core cuentas` (529/529 OK) en cada
      commit; falta bandit, coverage --fail-under=70 y gates de frontend
- [ ] Fase 4 (docs/CAMBIOS-*.md + PR body)
