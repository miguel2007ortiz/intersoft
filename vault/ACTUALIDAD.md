# ACTUALIDAD — estado y pendientes del proyecto

Bitácora de estado al corte para retomar sesión. **Supervisor (Claude) y
ejecutor (OpenCode): leer esto primero en cada arranque**, además de
`vault/INDICE.md` (regla 1.1 de `AGENTS.md`).

Última actualización: 2026-09-11 (#16 y #17 mergeados a `main` vía PR #3 y
PR #4, con CI real en verde y aprobación explícita del usuario).

> **#16 y #17: implementados por OpenCode, revisados por Claude, mergeados.**
> - `fix/confirmacion-desactivar-usuario` (commit `78a0fd3`) → **PR #3**
>   (merge commit `5a1df36`): desactivar en `/admin/usuarios` pide
>   confirmación (`ConfirmacionService.pedir`, destructivo), igual que
>   `empleados.component.ts`; reactivar sigue directo. CI real: 3/3 jobs
>   verdes (run `34552871214`).
> - `fix/validacion-rango-fechas` (commits `ec3dd1d`, `0d8e035`) → **PR #4**
>   (merge commit `3cc5879`): backend `FiltrosDashboard` rechaza
>   `fecha_inicio > fecha_fin` con 400 `FILTROS_INVALIDOS` (cubre dashboard,
>   reportes JSON y export Excel/PDF); frontend deshabilita
>   Aplicar/Generar/Excel/PDF y avisa. Bonus: se alineó ese path al contrato
>   `{codigo, detalle, errores}` (clave aditiva) y se corrigió el test
>   preexistente de reporte que usaba tipo `ventas` inválido. CI real: 3/3
>   jobs verdes (run `34552890748`).
> - Ambas ramas se habían creado solo en local (no en `origin`); se
>   pushearon antes de abrir los PR. `origin/main` pasó de `6fe8aca` a
>   `3cc5879`. Ramas `fix/*` intactas, sin borrar.
> - Follow-up abierto (no bloqueante): `/api/ventas/` (listado) tiene su
>   propia validación de fechas, solo de formato, sin chequeo de rango —
>   fuera del alcance de #17; decidir si entra en otra tarea.

---

## Rama y repositorio

- **`main` actualizado**: `origin/main` en `3cc5879` (`1c2f2f4` → `6fe8aca`
  vía PR #2 → `3cc5879` vía PR #3 + PR #4, los tres aprobados explícitamente
  por el usuario tras dictamen del supervisor).
- Ramas de trabajo `intersoft_miguel`, `fix/confirmacion-desactivar-usuario`,
  `fix/validacion-rango-fechas` quedan intactas, sin eliminar, ya integradas
  en `main`.
- PRs: #2 (`docs/PR-BODY-12.md`), #3
  (https://github.com/miguel2007ortiz/intersoft/pull/3, #16), #4
  (https://github.com/miguel2007ortiz/intersoft/pull/4, #17). Los tres:
  **MERGED**.

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

## PENDIENTE 3 — RESUELTO: #16 y #17 (UX/lógica real del admin), implementados y mergeados

Revisión distinta a la auditoría de código de `vault/auditoria-bugs-opencode.md`
(#1-#15, ya cerrada): esta buscó fallos que un admin real pisaría por lógica
de negocio o inconsistencia de UX, no vulnerabilidades. Encontrados por
Claude leyendo código, implementados por OpenCode, revisados y mergeados por
Claude con aprobación explícita del usuario.

**#16 — Desactivar cuenta en `/admin/usuarios` no pedía confirmación (sí en
`/empleados` para la misma acción) — corregido:**
- Hallazgo: `usuarios.component.ts::alternarActivo` llamaba a
  `desactivarUsuario`/`reactivarUsuario` directo al click, sin
  `ConfirmacionService`, a diferencia de `empleados.component.ts`,
  `roles.component.ts` y `clientes.component.ts`. Relevante porque
  `/admin/usuarios` puede desactivar cualquier cuenta de la empresa,
  incluida otro ADMINISTRADOR.
- Fix: `commit 78a0fd3` — `alternarActivo` ahora pide confirmación
  (`ConfirmacionService.pedir`) solo al desactivar; reactivar sigue directo.
  `+1` spec de regresión (confirmar/cancelar).
- Merge: **PR #3**, merge commit `5a1df36`, CI real 3/3 jobs verdes
  (run `34552871214`).

**#17 — Filtros de fecha de Dashboard/Reportes no validaban el rango — corregido:**
- Hallazgo: ni frontend ni backend comprobaban `fecha_inicio ≤ fecha_fin`;
  un rango invertido daba 0 filas sin ningún aviso, incluidos los reportes
  exportados a Excel/PDF.
- Fix: `commits ec3dd1d` + `0d8e035` — backend `FiltrosDashboard` levanta
  `ValueError` → 400 `FILTROS_INVALIDOS` con `errores: None` (contrato
  completo); frontend deshabilita Aplicar/Generar/Excel/PDF y avisa en
  pantalla. De paso corrigió un test preexistente con `tipo=ventas`
  inválido (`tests_fase5.py`).
- Merge: **PR #4**, merge commit `3cc5879`, CI real 3/3 jobs verdes
  (run `34552890748`).
- Follow-up no bloqueante: `/api/ventas/` (listado) valida formato de fecha
  pero no rango — fuera de alcance de #17, pendiente decidir si entra en
  otra tarea.

Ninguno de los dos tocó módulos cerrados de la auditoría original ni
invariantes de `AGENTS.md` §3.

## Pendientes de riesgo menores (no bloqueantes)

- `docs/RIESGOS.md` §pendientes: cámaras (video en vivo/transcodificación),
  volumen de datos (materializar/archivar), media a S3 (requiere
  `django-storages`, gate de supervisor).
- Auditoría cerrada: #1–#17 fixeados o revisados (#7 revisado sin bug activo).

## Flujo acordado

1. Leer `AGENTS.md` §1.1 + `docs/INDICE.md` + `vault/INDICE.md` + este archivo.
2. `main` está al día (`3cc5879`, PR #2 + #3 + #4). Próximo trabajo debería
   partir de `main` actualizado.
3. No push a `main` sin revisión de Claude. Commits Conventional Commits.