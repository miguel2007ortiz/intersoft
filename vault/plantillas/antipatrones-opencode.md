# Anti-patrones recurrentes (prompt para OpenCode)

> Extraído de `vault/auditoria-bugs-opencode.md` (15 hallazgos reales, #1-#15).
> Pegar como checklist ANTES de reportar "listo" en cualquier fix nuevo — son
> los mismos 10 patrones que causaron los 15 bugs encontrados hasta ahora.

---

**CHECKLIST ANTI-PATRONES — correr antes de dar un fix por terminado**

Antes de reportar el gate como verde, repasá tu propio diff contra esta lista.
Si tu cambio toca alguno de estos puntos y no lo cubriste, no está listo:

1. **Interpolación sin escapar** (#1, #11): ¿el código arma HTML/CSV/SQL/shell
   concatenando o interpolando un valor que viene de datos de usuario/DB
   (nombre de producto, cliente, empresa)? Usá `django.utils.html.escape` /
   `format_html` para HTML; prefijo de comilla para celdas CSV que empiecen
   con `= + - @`. Grep útil: `f"` o `f'` cerca de `.html`/`<`/`response.write`.

2. **I/O externo (red, SOAP, HTTP a terceros) dentro de un lock o
   `transaction.atomic()`** (#2): si el código hace `select_for_update()` o
   está en un `atomic()` y dentro llama a una API externa (DIAN, pasarela,
   IA), sacala del bloque: crear registro "pendiente", commit, llamar sin
   lock, aplicar resultado en una segunda transacción corta. Toda llamada
   externa nueva necesita timeout explícito (no dejar el default de la
   librería).

3. **Excepción de integridad esperada sin capturar** (#3): si un `.create()`
   puede chocar con un `unique=True` en un flujo de reintento normal (no un
   bug, un caso de negocio esperado), envolvé en
   `try/except IntegrityError` y devolvé un error de dominio (400 con el
   contrato `{codigo, detalle, errores}`), no dejes que reviente en 500.

4. **RBAC por nombre literal en vez de código de permiso** (#4): si estás
   escribiendo o tocando un `permissions.py`, no compares
   `perfil.rol.nombre == 'ADMINISTRADOR'`. Usá el código de permiso
   (`TienePermiso(codigo)`) para que roles personalizados por empresa
   funcionen. Siempre con guard: `perfil.rol is None` → denegar (403), nunca
   dejar que reviente `AttributeError`.

5. **Orden de efectos secundarios de dinero/stock** (#5, #6): en cualquier
   checkout/pago/reserva, preguntate: si el paso B falla, ¿el paso A (cobro,
   descuento de stock) queda revertido? Reservá/valida stock ANTES de cobrar,
   no al revés. Y cualquier `get_or_create`/"si no existe, crealo" sobre una
   fila compartida (carrito, contador) necesita lock o `atomic()`, no un
   `if`/`else` fuera de transacción.

6. **Doble fuente de verdad** (#7): si un signal (`post_save`/`post_delete`)
   recalcula un campo que la vista también calcula y guarda, hay dos lugares
   con la misma responsabilidad. No es automáticamente un bug, pero
   documentá cuál es la fuente de verdad real y verificá que todos los
   callers coincidan (si uno de los dos cambia, el otro puede quedar
   desincronizado sin que ningún test lo note).

7. **Reportes/estadísticas sin filtrar por estado** (#8): cualquier
   `Sum()`/`Count()`/agregado sobre ventas, facturas o pedidos que no filtre
   explícitamente por estado (excluir anuladas/pendientes/rechazadas según
   el reporte) va a inflar o inventar números. Filtrar por default, no dejar
   que el filtro sea opcional vía query param.

8. **Contrato de error roto** (#9, #10): toda respuesta de error de la API
   tiene que tener la forma `{codigo, detalle, errores}`, incluyendo el
   fallback de excepciones no controladas (500) y las respuestas de
   servicios degradados (502 de IA caída, etc). Si agregás un nuevo path de
   error, verificá contra ese contrato antes de reportar listo.

**Dos patrones extra, encontrados en el propio gate de CI (no en código de
negocio, pero igual de reales — #14, #15):**

9. **Config de CI que no refleja los defaults de la app** (#14): si
   `settings.py` cambia comportamiento según una variable de entorno
   (`DEBUG`, flags de seguridad), el pipeline de CI que fija esa variable
   tiene que fijar también TODAS las que dependen de ella, o el job va a
   fallar de forma silenciosa/masiva sin que sea un bug de negocio. Antes de
   tocar un workflow de CI, leé el bloque de `settings.py` que lee esa
   variable completo, no solo la línea que ibas a cambiar.

10. **Test/fixture con supuesto desactualizado** (#15): si un test de e2e o
    de integración asume un rol, permiso o dato de un usuario "demo" (ej.
    `ana@elprogreso.co` es ADMINISTRADOR), verificá esa afirmación contra el
    comando/fixture real que lo crea (`seed_demo.py` o equivalente) antes de
    escribir el test. Un comentario de test que describe algo que ya no es
    cierto en el seed es tan bug como el código — se detecta corriendo el
    test contra CI real, no confiando en el comentario.

**Regla general (aplica a los 10 puntos):** si tu fix toca uno de estos
patrones, agregá el test de regresión específico en el mismo commit
(nombre de producto malicioso, DIAN lenta, rol sin permiso, cobro con fallo
de stock simulado, agregado con venta anulada, excepción no-DRF forzada,
etc.) — no alcanza con que la suite existente siga en verde.
