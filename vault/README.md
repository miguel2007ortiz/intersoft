# Vault de trabajo — InterSoft

Vault de **notas de trabajo y decisiones informales** para consulta rápida del
equipo y de los agentes (Claude/OpenCode) durante una sesión. Es un
complemento, **no** una fuente de verdad: el contrato sigue siendo
`AGENTS.md` y la documentación formal de `docs/`.

## Estructura

| Ruta | Contenido |
|------|-----------|
| `README.md` | Este índice. |
| `decisiones.md` | Registro cronológico de decisiones tomadas (informal, sin fricción). |
| `plantillas/decision-nueva.md` | Plantilla para documentar una decisión nueva. |

## Cómo se usa

- **Abrir Obsidian** con la raíz del repo como vault: verá todos los `.md`
  (incluida `docs/` y `figma-marketplace/*guía.md`) con enlaces y grafo.
- `.obsidian/` (preferencias locales del workspace) **no se versiona**.
- Escribir aquí lo que no pertenece a `docs/`: resoluciones en caliente,
  pendientes menores, contexto de una decisión, reuniones.
- Cuando una nota madura y define un comportamiento observable o una
  invariante, se **promueve** a `docs/ROADMAP.md` o `docs/RIESGOS.md` (y se
  marca como "hecho" en el registro).

## Enlaces útiles

- Índice general → [docs/INDICE.md](../docs/INDICE.md)
- Contrato y gates → [AGENTS.md](../AGENTS.md)