# fix: correcciones críticas de auditoría (XSS reporte, DIAN fuera de transacción, RBAC fino, contrato de error, ESLint real, +9)

## Resumen

Auditoría de 13 hallazgos reales en backend (leídos directamente en código,
sin supuestos) y frontend, registrada en `vault/auditoria-bugs-opencode.md`.
Se corrigieron 12 con test de regresión (o gate verde) y commit atómico cada
uno; #7 se revisó y se confirmó que no es un bug activo (sin cambio de
código). Detalle completo, tabla de hallazgos y cuadro fix×gate en
`docs/CAMBIOS-2026-09-10.md`.

## Commits incluidos

- `75dbc90` — #1 XSS almacenado en `exportar_html` + #11 CSV/formula injection en `exportar_csv`
- `17c1d0a` — #2 llamada DIAN dentro de `transaction.atomic()` sin timeout + #3 `IntegrityError` no capturado en nota crédito
- `f03b3b5` — #4 RBAC grueso hardcodeado, ignoraba roles personalizados y `perfil.rol is None`
- `fcc873f` — #5 pasarela cobra antes de reservar stock + #6 carrera en `_carrito_de`
- `6aa83bd` — #8 estadísticas de ventas infladas con anuladas/pendientes
- `9eee239` — #9 contrato de error 500 inconsistente + #10 `IA_NO_DISPONIBLE` sin `errores`
- `b1a2ca0` — #12 `numero_factura` ya no depende de que el caller bloquee `Empresa`
- `e6752f0` — docs: hash del commit anterior en el vault
- `197ba99` — #13 ESLint real (`@angular-eslint`) + 77 violaciones corregidas en `frontend/src/`
- `b42a10f` — #14 (gate de supervisor) `SECURE_SSL_REDIRECT=False` en el job backend de CI, que redirigía 301 todo con `DEBUG=False`
- `8689c4d` — #15 (gate de supervisor) el e2e del panel de Envios ahora inicia sesión como personal (EMPLEADO), no como la compradora (CLIENTE)

## Checklist `AGENTS.md` §4 — resultado real de la Fase 3

### Backend

- [x] `ruff check .` → `All checks passed!`
- [x] `bandit -c bandit.yaml -r . -q` → sin hallazgos, exit 0
- [x] `python manage.py check` → `System check identified no issues (0 silenced).`
- [x] `python manage.py makemigrations --check --dry-run` → `No changes detected`
- [x] `python manage.py test` → `Ran 625 tests` → `OK` (post-merge de `origin/main`)
- [x] `coverage run manage.py test core && coverage report --fail-under=70` → `Ran 549 tests` → `OK`; cobertura total **94%**
- [x] CI real de GitHub Actions, run `34538821092` sobre el PR #2
  (`intersoft_miguel` → `main`, HEAD `8689c4d`): job `Frontend` ✅ (42s),
  job `Backend` ✅ (4m20s, tras `b42a10f` #14 — antes: `611 tests`, `344
  failures + 122 errors` por `SECURE_SSL_REDIRECT`), job `E2E` ✅ (1m51s,
  tras `8689c4d` #15 — antes: 1 test en rojo de forma determinista en los
  3 runs anteriores). Los 3 jobs en verde sobre la misma rama/commit.
  https://github.com/miguel2007ortiz/intersoft/pull/2

### Frontend

- [x] `npm run lint` → `ng lint` (`All files pass linting.`) + `prettier --check` → `All matched files use Prettier code style!`
- [x] `npm run build` → build completo, bundle inicial 320.54 kB raw / 87.44 kB transferencia estimada (dentro de presupuesto)
- [x] `npm run test:ci` → `Test Files 21 passed (21)`, `Tests 96 passed (96)`

Todos los gates de esta ronda pasan sobre el estado final de la rama.

## Riesgos

- Los fixes de #5/#6 y #12 tocan rutas críticas de dinero/stock (checkout,
  creación de venta); se mitigó con tests de concurrencia dedicados
  (`ConcurrenciaCheckout`, `ConcurrenciaNumeroFactura` en
  `core/tests_fase5.py`) además de la suite completa en verde.
- #9/#10 cambian el shape de dos respuestas de error; el frontend
  (`django-error.util.ts`) ya toleraba variaciones de `codigo`/`errores`
  ausentes, así que no requirió cambios, pero vale doble chequeo visual en
  QA de los flujos de error 500 y del asistente IA caído.
- #13 toca 31 archivos de frontend (config de ESLint + fixes mecánicos y de
  accesibilidad); ningún cambio afecta lógica de negocio, solo linting,
  tipos y semántica de plantillas — mitigado con la suite completa de
  frontend en verde (21 archivos, 96 tests) tras el cambio.
- #7 no tiene cambio de código: el riesgo de un reviewer es asumir que "sin
  fix" significa "no revisado" — la justificación de por qué no se tocó
  código está en `vault/auditoria-bugs-opencode.md` y en `docs/RIESGOS.md`
  (pendiente 8 de esa sección).
- #14 no viene de la auditoría original sino del gate de supervisor
  (`vault/plantillas/revision-merge.md`): el job `backend` de
  `.github/workflows/ci.yml` nunca había pasado en verde (dos runs
  registrados en GitHub Actions, ambos en `failure`) por
  `SECURE_SSL_REDIRECT`/`SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` sin
  fijar con `DEBUG=False`. El fix es solo de config de CI, no toca
  `settings.py` ni ningún módulo cerrado; verificado localmente
  reproduciendo el env exacto del pipeline (625 tests en 0).
- #15 tampoco viene de la auditoría original: con #14 corregido, el job
  `e2e` seguía en rojo de forma 100% determinista (2 runs + 1 rerun) por
  un test que asumía que `ana@elprogreso.co` es ADMINISTRADOR, cuando
  `seed_demo.py` la crea CLIENTE — `personalGuard` la redirige
  correctamente, así que era el test el equivocado, no la app. Fix solo en
  `frontend/e2e/tienda-flujo.spec.ts`; verificado local (3/3).

## Rollback

En orden inverso al de aplicación (`git revert`, no `reset`, sobre rama ya
pusheada):

```
git revert b42a10f   # #14 SECURE_SSL_REDIRECT en CI
git revert 197ba99   # #13 ESLint frontend
git revert b1a2ca0   # #12 numero_factura
git revert 9eee239   # #9 + #10 contrato de error
git revert 6aa83bd   # #8 estadisticas de ventas
git revert fcc873f   # #5 + #6 checkout / carrito
git revert f03b3b5   # #4 RBAC
git revert 17c1d0a   # #2 + #3 DIAN / nota credito
git revert 75dbc90   # #1 + #11 XSS / CSV injection
```

Cada commit es independiente; revertir uno solo no debería arrastrar a los
demás.

## Nota para el revisor

Revisar primero `core/analytics.py` (`exportar_html`, el hallazgo crítico de
XSS) y `core/views_facturacion.py` (llamada DIAN + nota crédito, los otros
dos hallazgos 🔴). El resto son 🟠/🟢 de menor impacto pero igual de
reales — detalle uno por uno en `docs/CAMBIOS-2026-09-10.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
