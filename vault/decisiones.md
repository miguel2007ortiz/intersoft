# Registro de decisiones — InterSoft

Registro cronológico **informal** de decisiones tomadas durante el trabajo.
Formato liviano: cuando una decisión madura se promueve a
`docs/ROADMAP.md` (sección "Decisiones abiertas / resueltas") o a
`docs/RIESGOS.md`.

## 2026

- **Cache de BD por generación (B1)**: invalidación por namespace+generación
  con backend de BD (no existe `delete_pattern` en MySQL); evita
  `cache.clear()` global. → `docs/ROADMAP.md` B1, `core/cache_key.py`.
- **Paginador clásico en catálogo (B2)** en vez de infinite scroll: el
  catálogo está cacheado 60s y el grid de 24 admite navegación predecible.
- **DIAN con mock por defecto**: `DIAN_MOCK=True` hasta habilitación real con
  credenciales; los cambios a la integración DIAN pasan por revisión manual
  (invariante §3 de `AGENTS.md`).
- **Envíos (F1/F2)**: módulo de despachos del marketplace (1:1 `Envio`↔`Venta`,
  máquina de estados, checkout exige dirección). El "enviso" del README era el
  módulo de envíos, no una herramienta externa.
- **Cámaras (G1/G2)**: catálogo de grabaciones con metadatos en BD
  (`Grabacion`) + sincronización por disco; **sin** streaming en vivo ni
  transcodificación (lienzo deliberado). `disponible`/`url` se recalculan
  contra disco al serializar.
- **Figma**: carpeta `figma-marketplace/` (capturas + guías + tokens)
  **restaurada al repo** desde un commit huérfano; panel administrativo
  capturado con Playwright (sesión ADMINISTRADOR), regenerable con
  `frontend/scripts/capturas-figma-admin.mjs`. `figma-marketplace/` ya no es
  "no versionada" (decisión de supervisor).
- **Obsidian**: vault = raíz del repo; `.obsidian/` ignorado en git;
  `vault/` para notas informales y `docs/INDICE.md` como MOC.
- **`fix/qa-fase-2-seguridad` → SUPERSEDED (2026-10-01)**: no se mergea a
  `main`. Su contenido (buges BUG-09/13/19/05/03/18/22/24/26 del QA FASE-2/0-1)
  ya quedó integrado en `main` por las ramas del 17–24/09 con diseños más
  nuevos e incompatibles (bloqueo por intentos como campo del modelo en vez de
  tabla `IntentoLoginFallido`; migraciones con grafos distintos en `cuentas`).
  Un merge forzado regresa 14 archivos en conflicto y rompe la invariante de
  migraciones de `docs/RIESGOS.md`. Decisión del supervisor (corte
  2026-10-01). Los `docs/PR-BODY-*.md` y `docs/QA-correcciones.md` del QA
  reflejan esa versión obsoleta y no representan el estado de `main`.
- **Fix de CI del corte 2026-10-01** → `7f10bcf` push + PR a `main`:
  `ConfiguracionSeguridadProduccionTest` debe restaurar `SECRET_KEY`/`DEBUG`
  (snapshot de entorno) antes del `importlib.reload`, porque en CI no existe
  `.env` y el fail-fast de arranque tumba el job `backend` con 9 errores.
- **CI fiable (2026-10-01)** → `chore/ci-pin-ubuntu-24-actions-v7` merged a
  `main` (`7dc2611`): runner pineado a `ubuntu-24.04` (no `ubuntu-latest`) para
  que la migración programada de `ubuntu-latest` → 26.04 no rompa el pipeline;
  actions subidas al tag actual (checkout/setup-node/setup-python v7, Node 24,
  fuera de la deprecación de Node 20). Verificado: Backend y E2E verdes en el
  PR y post-merge; Frontend sigue rojo **solo** por `npm audit` preexistente
  (`@angular/router <22.2.0`, GHSA-ff3f-86qr-9cv3, y `brace-expansion`) —
  pendiente de resolver subiendo Angular a `^22.2.0` en tarea aparte.
- **OpenCode agente único y autónomo (2026-10-01)** → `chore/opencode-agente-unico`
  merged a `main` (`f6ecae9`): se elimina el rol de supervisor (Claude).
  `AGENTS.md` reescrito como contrato de agente único (flujo §2, gates §4,
  aprobaciones §7); `opencode.json` habilita `git push`/`git merge`/`gh pr
  merge` en `allow` (autonomía; docker/despliegue siguen `ask`, destructivos
  `deny`). Índices y plantilla `revision-merge.md` actualizados (checklist
  propio, no prompt de supervisor). Las notas históricas
  (`vault/decisiones.md`, auditoría, `docs/RIESGOS.md`, `PR-BODY-*.md`)
  conservan las menciones a Claude por decisión del usuario (registro
  histórico, no se falsifica).
- **Angular ^22.2.1 (2026-10-06)** → `fix/angular-22-2-1-audit` merged a
  `main` (`8dd3584`): sube los paquetes `@angular/*` 22.1.x → 22.2.1 para
  cerrar el advisory GHSA-ff3f-86qr-9cv3 (`@angular/router <22.2.0`, el
  `npm audit` que mantenía rojo el job Frontend de CI desde 24/09) y las
  transitivas de `brace-expansion`. Verificado: `npm audit` → 0
  vulnerabilidades; lint/build/134 tests locales OK; **CI completo en verde
  por primera vez** (Frontend incl. audit + Backend + E2E). Primer PNG con
  los 3 jobs en verde.
- **B4 — Volumen de datos: índices de apoyo a la analítica (2026-10-06)** →
  `feature/volumen-datos-indices-analitica` merged a `main` (`ab55847`): los
  dashboards/reportes (`vw_*` + `analytics.py`) agregan el histórico completo;
  se añaden 3 índices compuestos **aditivos** (migración `core/0025`) para
  las agregaciones más costosas — `detventa_prod_venta_idx`
  (DetalleVenta producto→vw_top_productos), `mov_prod_tipo_idx`
  (MovimientoInventario producto+tipo→vw_rotacion) y `prod_emp_activo_cat_idx`
  (Producto empresa+activo+categoria→vw_valor_inventario/bajo mínimo).
  Sin cambios destructivos ni de lógica de dinero; reversible con migrate.
  El **plan de archivado** de ventas viejas (`completada` > N, tablas fuera
  del ciclo activo, vistas con UNION, invariante `Venta.total` respetada)
  queda documentado en `docs/RIESGOS.md` §4 como siguiente paso, no
  implementado. Gates: 750 tests backend OK, cobertura 82% (70%), ruff/bandit
  limpios, `makemigrations --check` sin cambios, frontend 134 tests OK,
  **CI 3/3 verde**. Test de regresión: `core/tests_volumen.py` (los índices
  existen en el esquema real, no solo en el modelo).

## Formato de una entrada nueva

Ver plantilla → [`plantillas/decision-nueva.md`](plantillas/decision-nueva.md).