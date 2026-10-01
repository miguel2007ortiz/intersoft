# Revisión y merge de rama (gate de OpenCode)

Checklist que OpenCode ejecuta sobre una rama de trabajo **antes de mergear a
`main`** conforme a `AGENTS.md` §2/§4/§7. Se aplica a su propio trabajo (agente
único, sin supervisor); el resultado queda como reporte en el PR.

---

**REVISIÓN Y MERGE — `<rama>` → `main` (gate de OpenCode)**

**Contexto:** <2-3 líneas: qué trae la rama, HEAD y si está en sync con origin,
qué quedó pendiente de la sesión anterior.>

**Qué contiene la rama (commits relevantes):**
- <hash> <mensaje abreviado — por commit clave>

**Gates verificados por OpenCode sobre HEAD:**
- Backend: `ruff`, `bandit`, `check`, `makemigrations --check --dry-run` ✅;
  suite completa **<N> tests OK**; cobertura core **<X>%** (gate 70%).
- Frontend: `npm run lint` ✅ (ESLint real); `npm run build` ✅ (budgets);
  `npm run test:ci` ✅ **<N> tests**; e2e Playwright ✅.
- Recon: sin `.env`/claves trackeados; `.obsidian` ignorado. Servidores local up.

**Checklist de OpenCode antes de mergear:**
1. Revisar el diff contra `main`, con foco en <qué revisar: arquitectura, a11y,
   contratos>. Confirmar que no se violan invariantes de `AGENTS.md` §3
   (multi-tenant, `select_for_update`, DIAN mock, contrato de errores
   `{codigo,detalle,errores}`).
2. Verificar CI (`.github/workflows/ci.yml`) verde para la rama y, si todo
   pasa, **mergear a `main`** (flujo §2: solo desde rama verde; no hay
   `develop` en este repo).
3. Actualizar si aplica: `docs/CAMBIOS-*.md`, `docs/RIESGOS.md`,
   `docs/PR-BODY-*.md`, `vault/ACTUALIDAD.md` (merge a main hecho, nuevo push).
4. No desplegar: despliegue = manual de `docs/DESPLIEGUE.md`, requiere
   aprobación explícita del humano (sección 7 de `AGENTS.md`).

**Notas para la revisión:**
- `vault/ACTUALIDAD.md` tiene el estado completo y pendientes para contrastar.
- Si el CI no está verde, OpenCode corrige en `<rama>` y re-corre los gates;
   no mergea "con fallas conocidas" salvo excepción explícita del humano,
   documentada en el PR.