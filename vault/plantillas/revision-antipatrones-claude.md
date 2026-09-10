# Revisión de anti-patrones (prompt para Claude, supervisor)

> Complementa `revision-merge.md`. Ese template verifica CI/invariantes de
> `AGENTS.md` §3; este busca específicamente los mismos 10 patrones que
> generaron los 15 hallazgos de `vault/auditoria-bugs-opencode.md`. Correr
> sobre el diff de cualquier rama de OpenCode antes de aprobar merge, sin
> confiar en que el ejecutor ya se autorevisó con
> `antipatrones-opencode.md`.

---

**REVISIÓN DE ANTI-PATRONES — diff `<rama>` contra `main`**

Sos el supervisor. No confíes en el reporte de "gates verdes" del ejecutor
sin releer el diff línea por línea contra esta lista. Cada punto tiene el
grep/lectura mínima que lo detecta:

1. **XSS/injection por interpolación cruda.** Grep `f"` / `f'` / `+ str(` en
   cualquier archivo que arme HTML, CSV, SQL crudo o comandos de shell cerca
   de un valor que venga de `request.data`, un modelo con campo de texto
   libre (nombre, dirección) o un query param. Si hay match, confirmar que
   pasa por `escape`/`format_html`/prefijo CSV antes de salir.

2. **Llamada externa dentro de lock.** Buscar `select_for_update` o
   `transaction.atomic` en el archivo tocado; si en el mismo bloque hay una
   llamada a `requests.`, un cliente SOAP/zeep, una pasarela de pago o
   cualquier IA externa, es un hallazgo — aunque hoy esté mockeado
   (`DIAN_MOCK`/`PASARELA_MOCK`/`IA_PROVIDER`), el código de producción real
   bloquea una fila mientras espera una respuesta de red. Confirmar timeout
   explícito en el cliente.

3. **`.create()`/`.save()` sin capturar `IntegrityError`** cuando el modelo
   tiene un `unique=True` y el flujo permite reintentos de negocio (nota
   crédito, factura, pago). Si no hay `try/except`, es 500 en vez de error
   de dominio.

4. **RBAC por string.** Grep `.rol.nombre ==` o comparaciones literales de
   rol en `permissions.py`/vistas. Debe ser por código de permiso
   (`TienePermiso`). Confirmar guard explícito para `rol is None`.

5. **Orden dinero/stock.** En cualquier vista de checkout/pago/venta nueva
   o modificada: ¿el cobro (pasarela) ocurre antes o después de la
   reserva/validación de stock dentro del mismo `atomic()`? Debe reservar
   primero. Y todo `get_or_create` sobre una fila compartida (carrito,
   contador, saldo) debe estar bajo lock, no un `if existe: ... else: crea`
   fuera de transacción.

6. **Doble fuente de verdad.** Si un signal (`post_save`/`post_delete`)
   toca un campo que una vista también setea, confirmar cuál gana y que
   ambos caminos de código (todas las vistas que crean/editan ese modelo)
   sean consistentes entre sí. Si no lo son, es un hallazgo aunque hoy
   "funcione por casualidad".

7. **Agregados sin filtro de estado.** Grep `Sum(` / `Count(` /
   `Aggregate(` en vistas de reportes/estadísticas; confirmar que el
   queryset base excluye anuladas/pendientes/rechazadas por default, no
   solo cuando el cliente manda un query param.

8. **Contrato de error.** Cualquier `return Response(...)` o excepción
   nueva de error debe tener `{codigo, detalle, errores}`. Prestar
   atención especial a paths de servicios degradados (IA, pasarela, DIAN
   caídos) y al manejador de excepción no controlada — son los que más se
   olvidan.

9. **CI no espeja los defaults de settings.** Si el diff toca
   `.github/workflows/ci.yml` o cualquier variable de entorno que
   `settings.py` lee condicionalmente (`DEBUG`, flags de seguridad,
   `ALLOWED_HOSTS`), leer el bloque completo de `settings.py` que depende de
   esa variable — no solo confiar en que "el job pasó localmente", correr
   CI real (push a rama/PR, ver `revision-merge.md`) antes de aprobar.

10. **Fixture/test con supuesto no verificado.** Si un test nuevo o tocado
    asume un rol/permiso/estado de un usuario demo o un dato de seed,
    confirmar contra el comando de seed real (`seed_demo.py` u otro), no
    contra el comentario del test. Si el comentario y el seed no coinciden,
    el test es el bug.

**Cómo usar esto junto con `revision-merge.md`:**
- `revision-merge.md` cubre el gate de proceso (CI verde, invariantes de
  `AGENTS.md` §3, docs actualizadas, aprobación de merge).
- Este archivo cubre el contenido del diff en sí — los patrones concretos
  que ya causaron bugs reales en este repo. Correr ambos antes de aprobar
  un merge a `main`.
- Si el ejecutor fue OpenCode con `antipatrones-opencode.md` cargado, este
  checklist es la segunda mirada, no un sustituto — dos de los 15 hallazgos
  (#14, #15) se encontraron precisamente porque nadie había hecho esta
  segunda pasada con CI real antes.
