# BUG-20 — detalle de venta

Rama `fix/qa-bug-20-detalle-venta`, 1 commit desde `main`. Alcance deliberadamente
estrecho para no chocar con la Fase 5 en curso.

## Qué faltaba

El backend **ya devolvía todo lo necesario y ya filtraba por empresa**. No hizo
falta tocar ningún serializer:

- `VentaLecturaSerializer` ya trae número de factura, fecha, cliente con
  documento, vendedor, método de pago, estado, subtotal, descuento, total y
  `total_items`.
- `DetalleVentaLecturaSerializer` ya trae producto, nombre, SKU, cantidad,
  precio unitario y subtotal de línea.
- `VentaDetalleView.get` ya filtra por `empresa=_obtener_empresa(request)`.

Lo que faltaba era la pantalla, y una prueba que **fijara** ese aislamiento para
que un refactor futuro no lo pierda en silencio.

## Qué se hizo

### Backend — solo pruebas

`GET /api/ventas/<uuid>/` verificado con dos empresas:

- El detalle propio responde 200 con encabezado, líneas y totales.
- Una venta de otra empresa responde **404**, no 403 ni 200: el id de otro
  tenant no se confirma ni siquiera negando el acceso.
- Verificado en los dos sentidos, y que cada empresa sí ve la suya — así queda
  claro que el 404 es por empresa y no por permisos.
- El anónimo recibe 401.

Sin cambios de código en el backend, por tanto **sin cambios de contrato**.

### Frontend

- Ruta `/ventas/:id` con los mismos guards que el listado. El aislamiento no
  depende de esta pantalla: lo garantiza el 404 del backend.
- Encabezado con número, fecha, cliente (con documento), vendedor, método de
  pago y estado; tabla de líneas; totales.
- **Los importes se pintan tal cual llegan del API.** Recalcularlos en el
  cliente abriría la puerta a que la pantalla y la factura digan cosas
  distintas por un redondeo. Queda un `TODO(BUG-21)` en el bloque de totales,
  donde irá la línea de IVA cuando el backend la desglose.
- Una venta anulada muestra la fecha y el motivo.
- La pantalla distingue «no existe o no es tuya» de un fallo de red: solo el
  segundo ofrece reintentar. Ofrecer «Reintentar» ante un 404 invita a repetir
  algo que nunca va a funcionar.

### Accesibilidad y navegación

- La fila del listado abre el detalle con **clic y con Enter** (`tabindex="0"`,
  `role="link"` y `aria-label` con el número de factura). Sin esto la única vía
  sería el ratón, porque un `<tr>` no es alcanzable con teclado.
- El botón «Anular» detiene la propagación para no abrir el detalle al pulsarlo.
- Foco visible en la fila navegable.

### Impresión

Botón «Imprimir» con `window.print()` y reglas `@media print`. **Sin librería de
PDF**: el navegador ya sabe imprimir.

- Carta por omisión (`@page { size: letter; margin: 14mm }`).
- Ticket de **80 mm** vía `@media print and (max-width: 80mm)`, que es lo que
  declara una impresora térmica de punto de venta: una columna, tipografía
  menor y márgenes de 3 mm.
- El menú lateral, la barra superior y los botones no se imprimen.
- `break-inside: avoid` en las filas para que una línea no se parta entre hojas.

## Verificación

| | |
|---|---|
| Backend `manage.py test` | **633 tests, OK** (línea base en `main`: 627) |
| `ruff check` | limpio |
| Frontend `npm run lint` | limpio |
| Frontend `npm run test:ci` | **110 tests, OK** (línea base: 103) |
| `ng build` | correcto |

Pruebas nuevas: 6 en backend y 7 en frontend.

## Restricciones respetadas

No se tocó ninguno de los archivos vetados por solaparse con la Fase 5:
`core/signals.py`, `recalcular_totales_venta`, `core/views_tienda.py`, los
modelos `Venta` y `DetalleVenta`, ni los datos semilla. **Sin migraciones.**
