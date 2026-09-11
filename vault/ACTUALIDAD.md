# ACTUALIDAD — estado y pendientes del proyecto

Bitácora de estado al corte para retomar sesión. **Supervisor (Claude) y
ejecutor (OpenCode): leer esto primero en cada arranque**, además de
`vault/INDICE.md` (regla 1.1 de `AGENTS.md`).

Última actualización: 2026-09-10 (PR #2 mergeado a `main`; además, revisión
de UX/lógica de negocio desde la experiencia del admin: 2 hallazgos nuevos
sin fix aún, #16 y #17).

---

## Rama y repositorio

- **`main` actualizado**: PR #2 (`intersoft_miguel` → `main`) mergeado
  (merge commit `6fe8aca`, aprobado explícitamente por el usuario tras el
  dictamen del supervisor). `origin/main` pasó de `1c2f2f4` a `6fe8aca`.
- Rama de trabajo `intersoft_miguel` (HEAD `71c1079`) queda intacta, sin
  eliminar, ya integrada en `main`.
- PR: https://github.com/miguel2007ortiz/intersoft/pull/2 — cuerpo en
  `docs/PR-BODY-12.md`. Estado: **MERGED**.

## Gates al corte (verificados hoy)

| Gate | Estado |
|---|---|
| Backend: `ruff`, `bandit`, `check`, `makemigrations --check --dry-run` | ✅ verdes sobre HEAD |
| Backend: `manage.py test` (suite completa) | ✅ 625 tests OK (verificado post-merge) |
| Backend: cobertura `core` | ✅ 549 tests, **94%** |
| Frontend: `npm run build` | ✅ OK (budgets intactos) |
| Frontend: `npm run test:ci` | ✅ 96 tests OK |
| Frontend: e2e Playwright | ✅ 3/3 |
| Frontend: `npm run lint` | ✅ verde — ESLint real resuelto (commit `197ba99`, #13 cerrado) |
| Servidores | API `127.0.0.1:8000` y SPA `127.0.0.1:4200` arriba |
| Seguridad | Sin `.env`/claves `.pem`/`.key` trackeados; `.obsidian` ignorado |

## PENDIENTE 1 (supervisor) — RESUELTO: gate de revisión corrido, PR #2 mergeado a `main`

Claude corrió `vault/plantillas/revision-merge.md` completo:

- Diff `origin/main..intersoft_miguel` revisado (nada de vuelta, fast-forward
  limpio); invariantes de `AGENTS.md` §3 no se tocaron por los fixes #1–#15.
- CI real disparada abriendo el PR #2 (no había otra forma: `ci.yml` no
  corre en push a rama de feature). En el primer run sobre `origin/main`
  (`1c2f2f4`, sin los fixes de esta rama) el job `backend` **ya estaba en
  rojo** (611 tests, 344 failures + 122 errors) — no es algo que esta rama
  rompió, es preexistente y quedó sin detectar porque nadie había corrido
  CI real antes.
- Encontrados y corregidos 2 hallazgos nuevos, fuera de la auditoría
  original, solo por correr el gate de CI real:
  - **#14**: job `backend` de CI nunca pasaba (`SECURE_SSL_REDIRECT` sin
    fijar con `DEBUG=False` → 301 en cada request) — `commit b42a10f`.
  - **#15**: job `e2e` fallaba 100% determinista (test de Envios con el
    usuario CLIENTE en vez del EMPLEADO) — `commit 8689c4d`.
- Run final `34538821092` sobre el PR: **Frontend ✅, Backend ✅, E2E ✅**,
  los 3 jobs en verde sobre el mismo commit (`8689c4d`).

**Dictamen del supervisor: la rama está lista para mergear a `main`.**
El usuario dio la aprobación explícita (`gh pr merge 2 --merge`) y Claude
ejecutó el merge: PR #2 en estado `MERGED`, merge commit `6fe8aca` sobre
`origin/main`. `intersoft_miguel` queda intacta (no se borró). No hay
pendientes de merge.

## PENDIENTE 2 — RESUELTO: `#13` ESLint real (cerrado por Claude)

Claude retomó y **terminó el #13** (commits `197ba99` + `3c0ae5f`, en
`origin/intersoft_miguel`):

- `197ba99 fix(frontend): ESLint real con @angular-eslint y 77 violaciones
  corregidas (#13)` — instaló `@eslint/js`, `angular-eslint 22.5.0`, `eslint
  ^10.9.1`, `typescript-eslint 8.69.0`; `eslint.config.js` flat config;
  target `ng lint` en `angular.json`; `"lint"` = `ng lint && prettier --check`;
  corrigió a11y real (`label for`+`id`, envolturas en `<label>`, key events +
  focusable) en todos los templates. `npm run lint` → exit 0.
- `3c0ae5f docs: cerrar #13` — actualizó `vault/auditoria-bugs-opencode.md`
  (13 hallazgos cerrados: 12 + revisado #7), `docs/CAMBIOS-2026-09-10.md`,
  `docs/RIESGOS.md` (§7 resuelto) y `docs/PR-BODY-12.md`.

**No queda ningún pendiente de la auditoría.** Cobertura de cobertura
post-fix pendiente de confirmar con gates frontend (build/test:ci).

## PENDIENTE 3 — nuevo: 2 hallazgos de UX/lógica real, sin fix (leídos en código)

Revisión distinta a la auditoría de código de `vault/auditoria-bugs-opencode.md`
(#1-#15, ya cerrada): esta busca fallos que un admin real pisaría por lógica
de negocio o inconsistencia de UX, no vulnerabilidades. Los dos siguientes
están confirmados leyendo código (frontend + backend), **sin corregir aún**.

**#16 — Desactivar cuenta en `/admin/usuarios` no pide confirmación (sí en
`/empleados` para la misma acción):**
- `frontend/src/app/features/administracion/usuarios/usuarios.component.ts:134-149`
  (`alternarActivo`) llama a `desactivarUsuario`/`reactivarUsuario` directo al
  click del botón (`usuarios.component.html:131-140`), sin `ConfirmacionService`.
- Contraste directo: `features/empleados/empleados.component.ts:218` (mismo
  verbo, "desactivar") sí pide confirmación con `ConfirmacionService` (su
  propio comentario lo dice: "Al desactivar se pide confirmacion"), igual que
  `roles.component.ts` y `clientes.component.ts`.
- Por qué importa para el admin: `/admin/usuarios` es la pantalla que puede
  desactivar **cualquier cuenta de la empresa, incluida otro ADMINISTRADOR**
  (la única excepción es la propia, oculta por `u.email !== auth.usuario()?.email`)
  — es la superficie más sensible de las cuatro y es la única sin el segundo
  clic de seguridad. Un click accidental en la fila equivocada bloquea el
  login de un compañero sin aviso ni deshacer visible.
- Fix sugerido (no aplicado): envolver `alternarActivo` con
  `this.confirmacion.confirmar({...})` cuando `usuario.activo` (igual patrón
  que `empleados.component.ts`); reactivar puede quedar sin confirmar.

**#17 — Filtros de fecha de Dashboard/Reportes no validan el rango
(`fecha_inicio` > `fecha_fin` o fechas futuras) ni frontend ni backend:**
- Frontend: `features/dashboard/dashboard.component.html:38-49` y
  `features/reportes/reportes.component.ts` (`filtros()`) mandan
  `fecha_inicio`/`fecha_fin` de un `<input type="date">` sin `min`/`max` ni
  chequeo de que inicio ≤ fin antes de pedir "Aplicar" o exportar.
- Backend: `backend/core/analytics.py` `FiltrosDashboard._fecha_valida`
  (línea ~48) solo valida el formato `YYYY-MM-DD`; nunca compara
  `fecha_inicio` contra `fecha_fin`. El `WHERE fecha BETWEEN inicio AND fin`
  con inicio > fin no da error, da **0 filas**.
- Por qué importa para el admin: si invierte las fechas sin querer (fácil en
  un `<input type="date">` con teclado), el dashboard y los reportes
  exportados (Excel/PDF vía `reportes.component.ts::exportar`) quedan vacíos
  sin ningún mensaje que diga "el rango es inválido" — parece que no hay
  ventas en el período en vez de avisar del error de captura. Mismo problema
  para fechas futuras (reporte "vacío" que en realidad es "todavía no pasó").
- Fix sugerido (no aplicado): en frontend, deshabilitar "Aplicar"/"Exportar"
  y mostrar mensaje si `fechaInicio() > fechaFin()`; en backend, que
  `FiltrosDashboard` levante el mismo `ValueError` que ya usa para
  `categoria` inválida cuando `fecha_inicio > fecha_fin` (un solo lugar,
  cubre dashboard, reportes y export a la vez).

Ninguno de los dos toca módulos cerrados de la auditoría original ni
invariantes de `AGENTS.md` §3; son candidatos a rama `fix/` propia si se
decide corregirlos.

## Pendientes de riesgo menores (no bloqueantes)

- `docs/RIESGOS.md` §pendientes: cámaras (video en vivo/transcodificación),
  volumen de datos (materializar/archivar), media a S3 (requiere
  `django-storages`, gate de supervisor).
- Auditoría cerrada: #1–#6, #8–#12 fixeados; #7 y #8 revisados/cerrados;
  #13 = este pendiente.

## Flujo acordado

1. Leer `AGENTS.md` §1.1 + `docs/INDICE.md` + `vault/INDICE.md` + este archivo.
2. `intersoft_miguel` ya está mergeada a `main` (PR #2, `6fe8aca`). Próximo
   trabajo debería partir de `main` actualizado.
3. No push a `main` sin revisión de Claude. Commits Conventional Commits.