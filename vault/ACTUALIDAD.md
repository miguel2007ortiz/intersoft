# ACTUALIDAD — estado y pendientes del proyecto

Bitácora de estado al corte para retomar sesión. **Supervisor (Claude) y
ejecutor (OpenCode): leer esto primero en cada arranque**, además de
`vault/INDICE.md` (regla 1.1 de `AGENTS.md`).

Última actualización: 2026-09-10 (PR #2 mergeado a `main` con aprobación
explícita del usuario).

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