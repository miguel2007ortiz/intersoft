# ACTUALIDAD — estado y pendientes del proyecto

Bitácora de estado al corte para retomar sesión. **Supervisor (Claude) y
ejecutor (OpenCode): leer esto primero en cada arranque**, además de
`vault/INDICE.md` (regla 1.1 de `AGENTS.md`).

Última actualización: 2026-09-10 (actualizado tras gate de supervisor:
`vault/plantillas/revision-merge.md` corrido por Claude, PR #2 abierto y
CI real en verde).

---

## Rama y repositorio

- Rama de trabajo: `intersoft_miguel`, **en sync con `origin/intersoft_miguel`**
  (HEAD `8689c4d`, último push de Claude).
- `origin/main` en `1c2f2f4`; `intersoft_miguel` está estrictamente adelante
  (fast-forward posible, `git log origin/main..intersoft_miguel` no trae
  nada de vuelta). No hay `develop` (el flujo usa `main` + ramas por dev).
- **PR abierto**: https://github.com/miguel2007ortiz/intersoft/pull/2
  (`intersoft_miguel` → `main`), cuerpo en `docs/PR-BODY-12.md`. Se abrió
  para poder disparar CI real (`ci.yml` solo corre en push/PR contra
  `main`/`develop`, no en push a una rama de feature) — **no está mergeado**.

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

## PENDIENTE 1 (supervisor) — RESUELTO: gate de revisión corrido, merge a `main` pendiente de tu aprobación explícita

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
Falta un solo paso, deliberadamente no ejecutado por Claude: **la
aprobación explícita tuya para el merge/push a `main`** (`AGENTS.md`
línea 239: "`git push` a `main`/`develop`, merge de PR" requiere tu
aprobación explícita). El PR #2 queda abierto esperando esa aprobación;
Claude no lo mergeó.

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

## Pendientes de riesgo menores (no bloqueantes)

- `docs/RIESGOS.md` §pendientes: cámaras (video en vivo/transcodificación),
  volumen de datos (materializar/archivar), media a S3 (requiere
  `django-storages`, gate de supervisor).
- Auditoría cerrada: #1–#6, #8–#12 fixeados; #7 y #8 revisados/cerrados;
  #13 = este pendiente.

## Flujo acordado

1. Leer `AGENTS.md` §1.1 + `docs/INDICE.md` + `vault/INDICE.md` + este archivo.
2. Decidir con el supervisor el orden: pendiente real es solo el **merge de
   `intersoft_miguel` a `main`** (gate de revisión de Claude).
3. No push a `main` sin revisión de Claude. Commits Conventional Commits.