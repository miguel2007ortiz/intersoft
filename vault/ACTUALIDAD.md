# ACTUALIDAD — estado y pendientes del proyecto

Bitácora de estado al corte para retomar sesión. **Supervisor (Claude) y
ejecutor (OpenCode): leer esto primero en cada arranque**, además de
`vault/INDICE.md` (regla 1.1 de `AGENTS.md`).

Última actualización: 2026-09-10 (actualizado tras cierre de #13 por Claude).

---

## Rama y repositorio

- Rama de trabajo: `intersoft_miguel`, **en sync con `origin/intersoft_miguel`**
  (HEAD `3c0ae5f`, último push de Claude).
- `origin/main` en `1c2f2f4`; ya integrado (merge `d9494c5`). No hay `develop`
  (el flujo usa `main` + ramas por dev).

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

## PENDIENTE 1 (supervisor) — revisar y aprobar merge a `main`

`intersoft_miguel` contiene todo lo de perfil/interlocutor (Fase 2/3/4:
`IntentoPago` + pasarela `cobrar`, checkout reserva→cobro→confirmar, `Envio`
en la reserva, `Grabacion`, backups/monitoreo, auditoría de bugs #1–#12) y los
últimos docs (contadores 625/549/96, AGENTS.md vault §1.1, `vault/INDICE.md`,
`vault/ACTUALIDAD.md`). **Revisión de diffs y merge a `main` = gate de Claude
(no del ejecutor)**.

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