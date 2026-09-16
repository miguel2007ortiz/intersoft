# ACTUALIDAD — estado y pendientes del proyecto

Bitácora de estado al corte para retomar sesión. **Supervisor (Claude) y
ejecutor (OpenCode): leer esto primero en cada arranque**, además de
`vault/INDICE.md` (regla 1.1 de `AGENTS.md`).

Última actualización: 2026-09-16 (sesión QA: 26 defectos del informe
`Informe-QA-InterSoft.pdf` atendidos/revisados).

---

## Rama y repositorio

- Rama de trabajo actual: `fix/qa-informe-backend` (desde `origin/main`
  `3cc5879`). **Sin push todavía** (a la espera del reporte + aprobación).
- PR #2 abierto (`intersoft_miguel` → `main`, `docs/PR-BODY-12.md`) sigue
  pendiente de aprobación explícita; no se mergeó.

## Gates al corte (verificados el 16/09/2026)

| Gate | Estado |
|---|---|
| Backend: `ruff`, `bandit`, `check`, `makemigrations --check --dry-run` | ✅ verdes |
| Backend: `manage.py test` (suite completa) | ✅ **638 tests OK** (suite completa 2 veces: 211s y 203s) |
| Backend: cobertura `core` | ✅ **94%** (gate 70%) |
| Frontend: `npm run build` | ✅ OK (budgets intactos) |
| Frontend: `npm run test:ci` | ✅ **103 tests OK** (24 archivos) |
| Frontend: `npm run lint` (ng lint + prettier) | ✅ verde |
| Frontend: e2e Playwright | ⏸ no corrido localmente esta sesión (requiere backend + seed); no se tocó ningún archivo e2e |

## Defectos del informe QA atendidos en la rama fix

Resueltos (19):

- **BUG-01** URL absoluta de imagen de producto (backend
  `ProductoLecturaSerializer.get_imagen` + `context={"request": request}`;
  onerror en miniatura → `assets/sin-imagen.png`).
- **BUG-02** Paginación real en `/api/productos/`
  (`{resultados,total,pagina,por_pagina,total_paginas}`) + UI paginada.
- **BUG-03** Alerta de stock idempotente (`sincronizar_alerta_stock` +
  command `generar_alertas_stock` + comandos de seed que insertaban
  duplicados corregidos).
- **BUG-05** Login 8–29s → índice compuesto
  `act_usuario_fecha_idx` en `ActividadUsuario` (migración
  `cuentas/0010`) + login sin queries perezosas (reuso de `perfil_pre`).
- **BUG-09** Login: identidad única vía usuario autenticado (prelookup por
  email solo para controles de bloqueo/inactivo).
- **BUG-13** Conteo de usuarios por rol filtrado por empresa del solicitante.
- **BUG-14** Re-verificado: validaciones se limpian al corregir el campo
  (reactive forms, build actual) — no requería cambio.
- **BUG-15** Configuración muestra `empresa_nombre` (fallback `—`), no el UUID.
- **BUG-16** Cookie-banner: `pointer-events: none` en host + `auto` en la
  tarjeta (deja de interceptar clics).
- **BUG-18** `DEFAULT_RENDERER_CLASSES` → solo `JSONRenderer` fuera de DEBUG.
- **BUG-19** 401 uniforme `{codigo: CREDENCIALES_INVALIDAS}` sin
  `intentos_restantes` (deja de revelar enumeración de cuentas). Breaking
  change menor de contrato → ver "Desviaciones".
- **BUG-22** Pipe compartido `moneda` (es-CO) aplicado en Ventas e
  Inventario (módulos que mostraban cifra sin indicar moneda).
- **BUG-24** Inventario: buscador ya existía; paginación real añadida
  (backend `InventarioProductosView` + frontend con el patrón de Productos).
- **BUG-25** Botón Eliminar en productos siempre visible pero
  `[disabled]` con tooltip cuando el producto tiene ventas.
- **BUG-26** Reloj de bloqueo del login solo corre durante un bloqueo activo
  (se detiene al llegar a 0 o al destruirse).

Re-verificados/resueltos por build actual (sin cambio de código): BUG-04,
BUG-06, BUG-07, BUG-14.

## Desviaciones del plan original (declaradas explícitamente)

1. **BUG-19**: se suprimió `intentos_restantes` por completo del body 401
   (ni número ni null), no solo en el último intento. Respuesta idéntica
   exista o no el correo. Es un breaking change menor del contrato de API
   → exige revisión del supervisor (Claude), como marca `AGENTS.md` §3.
   Frontend actualizado en la misma tarea (modelo `ErrorAuth`, servicio y
   template del login).
2. **BUG-03/seed**: `seed_demo` no garantizaba los roles base antes de crear
   perfiles (`Perfil.rol` NOT NULL) — 7 tests de `tests_seed.py` fallaban en
   suite completa. Se añadió `call_command('seed_roles')` (idempotente) al
   inicio de `seed_demo.py`. Es arreglo preexistente dentro del módulo tocado.
3. **BUG-10, BUG-11, BUG-12, BUG-17, BUG-20, BUG-21**: **NO implementados**.
   Pendientes de confirmar alcance (cambios de flujo/modelo/migración que
   requieren decisión del supervisor antes de tocar invariantes). Ver abajo.

## Pendientes para decidir con el supervisor

- **BUG-10** ventas con 0 ítems y total >0 (origen en seed: sembrar con
  `DetalleVenta` o venta sin ítems). Requiere confirmar datos vs código.
- **BUG-11** dashboard: dos rangos de fecha (histórico vs actual).
- **BUG-12** comprador marketplace sin ficha `Cliente` (vincular en
  checkout o crear ficha automática).
- **BUG-17** refresh del token como cookie HttpOnly (cambio de flujo de
  sesión).
- **BUG-20** detalle de venta + comprobante/imprimir.
- **BUG-21** POS sin IVA (modelo/migración de impuesto).

## Notas

- Archivos sueltos en la raíz (`0`, `Claude outputs/`) NO se versionan.
- E2E Playwright no forma parte del gate local de esta rama (los specs no
  cambiaron); CI lo correrá con `seed_demo` + API local.