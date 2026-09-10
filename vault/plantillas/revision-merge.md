# Revisión y merge de rama (gate de supervisor)

Prompt reutilizable para que Claude (supervisor) revise una rama de trabajo y
decida el merge a `main` conforme a `AGENTS.md` §2/§7. Copiar/pegar en su
sesión, ajustando hashes, rama y contenido.

---

**REVISIÓN Y MERGE — `<rama>` → `main` (gate de supervisor)**

**Contexto:** <2-3 líneas: qué trae la rama, HEAD y si está en sync con origin,
qué quedó pendiente de la sesión anterior.>

**Qué contiene la rama (commits relevantes):**
- <hash> <mensaje abreviado — por commit clave>

**Gates verificados por el ejecutor sobre HEAD:**
- Backend: `ruff`, `bandit`, `check`, `makemigrations --check --dry-run` ✅;
  suite completa **<N> tests OK**; cobertura core **<X>%** (gate 70%).
- Frontend: `npm run lint` ✅ (ESLint real); `npm run build` ✅ (budgets);
  `npm run test:ci` ✅ **<N> tests**; e2e Playwright ✅.
- Recon: sin `.env`/claves trackeados; `.obsidian` ignorado. Servidores local up.

**Tu tarea (supervisor):**
1. Revisar el diff contra `main`, con foco en <qué revisar: arquitectura, a11y,
   contratos>. Confirmar que no se violan invariantes de `AGENTS.md` §3
   (multi-tenant, `select_for_update`, DIAN mock, contrato de errores
   `{codigo,detalle,errores}`).
2. Verificar CI (`.github/workflows/ci.yml`) verde para la rama y, si todo
   pasa, **aprobar el merge a `main`** (flujo §2: solo desde rama verde; no
   hay `develop` en este repo).
3. Actualizar si aplica: `docs/CAMBIOS-*.md`, `docs/RIESGOS.md`,
   `docs/PR-BODY-*.md`, `vault/ACTUALIDAD.md` (merge a main hecho, nuevo push).
4. No desplegar: despliegue = manual de `docs/DESPLIEGUE.md`, requiere tu
   aprobación explícita aparte.

**Notas para la revisión:**
- El ejecutor no toca `main`; espera tu dictamen. Si pides cambios, los
  ejecuta en `<rama>` y te rebota la revisión.
- `vault/ACTUALIDAD.md` tiene el estado completo y pendientes por si quieres
  contrastar.