# ACTUALIDAD — estado y pendientes del proyecto

Bitácora de estado al corte para retomar sesión. **Supervisor (Claude) y
ejecutor (OpenCode): leer esto primero en cada arranque**, además de
`vault/INDICE.md` (regla 1.1 de `AGENTS.md`).

Última actualización: 2026-09-10 (sesión de corte por límite de Claude).

---

## Rama y repositorio

- Rama de trabajo: `intersoft_miguel`, **en sync con `origin/intersoft_miguel`**
  (último push `20ad718..23a1dae`).
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
| Frontend: `npm run lint` | 🔴 **ROJO — #13 a medio hacer (ver abajo)** |
| Servidores | API `127.0.0.1:8000` y SPA `127.0.0.1:4200` arriba |
| Seguridad | Sin `.env`/claves `.pem`/`.key` trackeados; `.obsidian` ignorado |

## PENDIENTE 1 (supervisor) — revisar y aprobar merge a `main`

`intersoft_miguel` contiene todo lo de perfil/interlocutor (Fase 2/3/4:
`IntentoPago` + pasarela `cobrar`, checkout reserva→cobro→confirmar, `Envio`
en la reserva, `Grabacion`, backups/monitoreo, auditoría de bugs #1–#12) y los
últimos docs (contadores 625/549/96, AGENTS.md vault §1.1, `vault/INDICE.md`,
`vault/ACTUALIDAD.md`). **Revisión de diffs y merge a `main` = gate de Claude
(no del ejecutor)**.

## PENDIENTE 2 (supervisor) — terminar `#13` ESLint real (a medio hacer)

Claude instaló/configuró la infra de lint **y quedó en el working tree sin
commitear** al cortar la sesión. Nada de eso debe perderse; se dejó intacto.

**Archivos modificados/sin commitear (WIP):**
- `frontend/package.json` + `package-lock.json`: añade `@eslint/js ^10.0.1`,
  `angular-eslint 22.5.0`, `eslint ^10.9.1`, `typescript-eslint 8.69.0`;
  `"lint"` ahora es `ng lint && prettier --check ...`.
- `frontend/angular.json`: target de lint (builder) configurado.
- `frontend/eslint.config.js`: **nuevo (untracked)** — flat config con
  TS strict + `angular.configs.tsRecommended` + `templateRecommended` +
  `templateAccessibility`; sin supresiones.
- `.ts` con auto-fixes de ESLint (imports/loose) de Claude: `catalogo.service`,
  `tienda.service`, `temporizador.util.spec`, `roles`, `usuarios`,
  `clientes`, `productos`, `dashboard`, `empleados`, `inventario`,
  `catalogo`, `favoritos`, `pos` (component).
- Templates ya corregidos por Claude (patrón a11y real: `label for`+`id`, o
  input envuelto en `<label>`): `pos.component.html`, `inventario.component.html`,
  `pos.component.css`.

**Faltan (40 errores `ng lint`, en 10 templates):**
- `click-effects-key-events` + `interactive-supports-focus` en: `envios`,
  `facturacion`, `catalogo`, `favoritos`, `ventas`, `confirmacion`,
  `sidebar`, `welcome-overlay` (y algunos en `pos`/`inventario` todavía).
- `label-has-associated-control` en: `carrito`, `checkout`, `ventas`,
  `catalogo`.
- `role-has-required-aria` (`aria-selected`) en `catalogo` (línea 52).

**Cómo retomarlo:** seguir el patrón de Claude (a11y real, sin
`eslint-disable`), correr `npm run lint` hasta exit 0, y después
`npm run build`, `npm run test:ci` y `npm run test:e2e`. Luego commitea
`feat(frontend): ESLint real (@angular-eslint) en todo src/` y actualiza
`docs/RIESGOS.md` §pendientes #7 y `vault/auditoria-bugs-opencode.md` #13.

## Pendientes de riesgo menores (no bloqueantes)

- `docs/RIESGOS.md` §pendientes: cámaras (video en vivo/transcodificación),
  volumen de datos (materializar/archivar), media a S3 (requiere
  `django-storages`, gate de supervisor).
- Auditoría cerrada: #1–#6, #8–#12 fixeados; #7 y #8 revisados/cerrados;
  #13 = este pendiente.

## Flujo acordado

1. Leer `AGENTS.md` §1.1 + `docs/INDICE.md` + `vault/INDICE.md` + este archivo.
2. Continuar #13 (PENDIENTE 2) o decidir el orden con el supervisor.
3. No push a `main` sin revisión de Claude. Commits Conventional Commits.