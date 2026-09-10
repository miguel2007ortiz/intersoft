# Índice del vault — InterSoft

Mapa de contenidos de las notas de trabajo informales. Este archivo es el
punto de entrada que **Claude (supervisor) y OpenCode (ejecutor) deben leer
antes de iniciar una tarea** (ver la sección de consulta en `AGENTS.md`).

## Notas del vault
- [ACTUALIDAD.md](ACTUALIDAD.md) — estado actual, pendientes y rama (leer primero al retomar).
- [README.md](README.md) — qué es el vault y cómo se usa.
- [decisiones.md](decisiones.md) — registro informal de decisiones y su contexto.
- [auditoria-bugs-opencode.md](auditoria-bugs-opencode.md) — auditoría de bugs
  reales de OpenCode, hallazgos #1–#13 y su estado (fix/cerrado/pendiente).

## Plantillas
- [plantillas/decision-nueva.md](plantillas/decision-nueva.md) — plantilla para
  registrar una decisión nueva en `decisiones.md`.
- [plantillas/revision-merge.md](plantillas/revision-merge.md) — prompt para que
  el supervisor revise una rama y apruebe el merge a `main`.
- [plantillas/antipatrones-opencode.md](plantillas/antipatrones-opencode.md) —
  checklist de 10 anti-patrones (extraídos de los 15 hallazgos reales) para
  que OpenCode se autorevise antes de reportar un fix como listo.
- [plantillas/revision-antipatrones-claude.md](plantillas/revision-antipatrones-claude.md) —
  la misma lista de 10 anti-patrones, en versión "qué grepear/leer" para que
  el supervisor revise el diff antes de aprobar merge (complementa
  `revision-merge.md`).

## Cómo se usa
1. Al arrancar cada sesión, leer `docs/INDICE.md` (MOC del repo) y este índice.
2. Si una nota del vault contradice el plan de la tarea, declararlo en el
   reporte del ejecutor y no tocarlo en silencio.
3. Decisiones nuevas del trabajo → `decisiones.md` (usar la plantilla),
   **no** solo en el mensaje de commit.
4. Si una nota es solo de tu equipo y no debe versionarse, vive en la config
   local de Obsidian (`.obsidian/`, ignorada por git); lo que Claude/OpenCode
   necesitan ver debe estar aquí dentro (versionado).