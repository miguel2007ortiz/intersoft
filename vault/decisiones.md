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

## Formato de una entrada nueva

Ver plantilla → [`plantillas/decision-nueva.md`](plantillas/decision-nueva.md).