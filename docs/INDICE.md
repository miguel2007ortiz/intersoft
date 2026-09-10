# Índice de documentación — InterSoft

Mapa de contenidos (MOC) para navegar la documentación, también usable como
índice de un vault de Obsidian apuntado a la raíz del repo. Las notas de
trabajo y decisiones informales viven en `vault/`.

> Contrato del proyecto (no se reemplaza): `AGENTS.md` define los roles, los
> gates obligatorios y las invariantes que ningún agente puede romper.

## Documentos raíz
- [AGENTS.md](../AGENTS.md) — orquestación Claude + OpenCode, invariantes y gates.
- [README.md](../README.md) — requisitos exactos e instalación.
- [docs/INDICE.md](INDICE.md) — este mapa.

## Guías de referencia
- [docs/RIESGOS.md](RIESGOS.md) — riesgos resueltos/pendientes y cómo se cerraron.
- [docs/ROADMAP.md](ROADMAP.md) — mejoras priorizadas (fases A-G) y decisiones registradas.
- [docs/DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) — tokens y componentes del frontend (vivo).
- [docs/CHECKLIST-SEGURIDAD.md](CHECKLIST-SEGURIDAD.md) — checklist pre-despliegue y operativo.
- [docs/DESPLIEGUE.md](DESPLIEGUE.md) — despliegue reproducible (gunicorn + nginx + MySQL 8).
- [backend/README.md](../backend/README.md) — backend: setup, comandos operativos (backup_db, monitor, seed).
- [frontend/README.md](../frontend/README.md) — frontend: setup, calidad y tests.

## Diseño (Figma)
- [figma-marketplace/figma-guide.md](../figma-marketplace/figma-guide.md) — capturas y tokens del marketplace.
- [figma-marketplace/figma-guide-admin.md](../figma-marketplace/figma-guide-admin.md) — capturas del panel administrativo.

## Vault (notas de trabajo)
- [vault/README.md](../vault/README.md) — qué es el vault y cómo se usa.
- [vault/decisiones.md](../vault/decisiones.md) — registro informal de decisiones.
- [vault/plantillas/decision-nueva.md](../vault/plantillas/decision-nueva.md) — plantilla de nueva decisión.
- [vault/auditoria-bugs-opencode.md](../vault/auditoria-bugs-opencode.md) — auditoría de bugs reales + plan de prompts de 4 fases para OpenCode.

## Flujo habitual
1. Requisitos y arquitectura → `docs/ROADMAP.md` + `docs/RIESGOS.md`.
2. Implementación → contratos de `AGENTS.md` (gates §4, invariantes §3).
3. Seguridad/despliegue → `docs/CHECKLIST-SEGURIDAD.md`, `docs/DESPLIEGUE.md`.
4. Notas informales durante el trabajo → `vault/`.