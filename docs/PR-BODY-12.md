# fix: correcciones críticas de auditoría (XSS reporte, DIAN fuera de transacción, RBAC fino, contrato de error, +7)

## Resumen

Auditoría de 13 hallazgos reales en el backend (leídos directamente en
código, sin supuestos), registrada en `vault/auditoria-bugs-opencode.md`.
Se corrigieron 11 con test de regresión y commit atómico cada uno; #7 se
revisó y se confirmó que no es un bug activo (sin cambio de código); #13
queda documentado como deuda de infraestructura de frontend (armar ESLint
real), fuera de alcance de un fix quirúrgico. Detalle completo, tabla de
hallazgos y cuadro fix×gate en `docs/CAMBIOS-2026-09-10.md`.

## Commits incluidos

- `75dbc90` — #1 XSS almacenado en `exportar_html` + #11 CSV/formula injection en `exportar_csv`
- `17c1d0a` — #2 llamada DIAN dentro de `transaction.atomic()` sin timeout + #3 `IntegrityError` no capturado en nota crédito
- `f03b3b5` — #4 RBAC grueso hardcodeado, ignoraba roles personalizados y `perfil.rol is None`
- `fcc873f` — #5 pasarela cobra antes de reservar stock + #6 carrera en `_carrito_de`
- `6aa83bd` — #8 estadísticas de ventas infladas con anuladas/pendientes
- `9eee239` — #9 contrato de error 500 inconsistente + #10 `IA_NO_DISPONIBLE` sin `errores`
- `b1a2ca0` — #12 `numero_factura` ya no depende de que el caller bloquee `Empresa`
- `e6752f0` — docs: hash del commit anterior en el vault

## Checklist `AGENTS.md` §4 — resultado real de la Fase 3

### Backend

- [x] `ruff check .` → `All checks passed!`
- [x] `bandit -c bandit.yaml -r . -q` → sin hallazgos, exit 0
- [x] `python manage.py check` → `System check identified no issues (0 silenced).`
- [x] `python manage.py makemigrations --check --dry-run` → `No changes detected`
- [x] `python manage.py test` → `Ran 539 tests in 193.583s` → `OK`
- [x] `coverage run manage.py test core && coverage report --fail-under=70` → `Ran 463 tests` → `OK`; cobertura total **93%**

### Frontend

- [x] `npm run lint` → `All matched files use Prettier code style!`
- [x] `npm run build` → build completo, bundle inicial 314.38 kB raw / 86.02 kB transferencia estimada (dentro de presupuesto)
- [x] `npm run test:ci` → `Test Files 17 passed (17)`, `Tests 78 passed (78)`

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
- #7 y #13 no tienen cambio de código: el riesgo de un reviewer es asumir
  que "sin fix" significa "no revisado" — la justificación de por qué no se
  tocó código está en `vault/auditoria-bugs-opencode.md` y en
  `docs/RIESGOS.md` (pendientes 7 y 8 de esa sección).

## Rollback

En orden inverso al de aplicación (`git revert`, no `reset`, sobre rama ya
pusheada):

```
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
