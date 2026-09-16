# Bitácora de modo autónomo

Sesión iniciada el 2026-09-16 a las 10:05. Tres bloques: cerrar Fase 2, Fase 4
(productos e inventario) y BUG-20 (detalle de venta).

Este archivo es la memoria de la sesión: si el contexto se compacta, se relee
desde arriba antes de continuar.

## Entorno

- MySQL 8.0.30 de Laragon arrancado a mano (`mysqld --datadir=C:/laragon/data/mysql-8`).
  Hay que apagarlo al terminar la sesión.
- Prohibido en esta sesión: `push`, `merge`, `rebase`, `reset --hard`, tocar
  `backend/.env`, `flush`, `seed_demo`, borrar datos de `intersoft1_db`,
  reescribir migraciones ya commiteadas, instalar dependencias nuevas.

---

## BLOQUE A — cerrar Fase 2

### 10:05 — inicio

Rama `fix/qa-fase-2-seguridad`, árbol limpio. Pendiente: verificar las 691
pruebas y añadir la nota de configuración local de caché al cuerpo del PR.

### 10:15 — fin

- Suite backend: **691 pruebas, OK** (263 s). Árbol limpio antes y después.
- Añadida la sección «Configuración local» a `docs/PR-BODY-fase-2.md`: hay que
  comentar `CACHE_BACKEND` en `backend/.env` para que el desarrollo use
  `LocMemCache` y no dependa de `crear_cache`. El `.env` **no** se tocó.
- Commit: `6ff8bd2 docs(fase-2): nota de configuracion local de cache`.

**Fase 2 lista para PR.** Rama `fix/qa-fase-2-seguridad`, 10 commits, sin push.
Cuerpo del PR en `docs/PR-BODY-fase-2.md`.

---

## BLOQUE B — Fase 4: productos e inventario

### 10:16 — inicio, línea base en main

Línea base en `main` antes de tocar nada: **627 pruebas backend, OK**.
Frontend en `main`: 103 pruebas, lint y build limpios.

Aviso: la rama se creó por error desde `fix/qa-fase-2-seguridad`. Se borró y se
recreó desde `main` (`3cc5879`) antes de cualquier cambio. Efecto colateral: el
commit `6ff8bd2` de la Fase 2 arrastra una versión temprana de esta bitácora.

### 11:20 — BUG-01 (imágenes rotas en el panel) — HECHO

`/api/productos/` devolvía `/media/...` relativa y el catálogo la absoluta. El
`ImageField` de DRF solo construye la absoluta si el `request` está en el
contexto del serializer: el catálogo lo pasaba, el panel no.

- `core/serializers_base.py` con `ImagenAbsolutaMixin`, usado por los dos
  serializers de producto; las vistas del panel pasan el `request`.
- Frontend: `loading="lazy"` y respaldo en `(error)` con un SVG en data URI.
- Commit `79b7e09`. Pruebas: 5 backend + 1 frontend. Verificado que fallaban
  antes (13 fallos con el fix revertido).

### 11:45 — BUG-02 (imposible pasar del producto 50) — HECHO

`total` era el tamaño de la página, no los registros reales, y no había
parámetro `pagina`.

- `core/paginacion.py` extrae el patrón del catálogo público (COUNT real,
  techo de 200, `desde`/`hasta`). Orden `(nombre, id)`: el desempate evita que
  MySQL repita una fila en dos páginas y omita otra.
- El catálogo público usa el mismo helper **sin cambiar su contrato** (mismas
  claves, `por_pagina` fijo en 24, sigue sin aceptar `limite`).
- Frontend: `app-paginador` compartido, "Mostrando X-Y de N", conserva
  búsqueda y filtros; buscar o filtrar vuelve a la página 1.
- Commit `7e7934e`. Pruebas: 14 backend + 3 frontend.

Backend 19/19 en las clases nuevas; frontend 107/107.

### 12:30 — BUG-24 (inventario sin buscador ni paginación) — HECHO

El buscador con debounce de 300 ms ya existía; faltaba la paginación y que los
filtros se combinaran en el servidor.

- `/api/inventario/productos/` usa `core/paginacion.py`; los dos filtros se
  aplican en el backend (combinarlos en el cliente sobre la página ya recortada
  solo miraría los 50 primeros productos).
- `select_related('categoria')` quita una consulta por fila; la fila incluye
  `imagen` absoluta.
- Frontend: `app-paginador`; buscar o marcar «solo stock bajo» vuelve a la
  página 1. Spec nueva del componente (no tenía).
- Commit `c1c4585`. Pruebas: 10 backend (incluida una con dos empresas) + 4
  frontend.

### 12:50 — BUG-25 (Eliminar aparece y desaparece) — HECHO

- Botón siempre visible; deshabilitado con `title` + `aria-describedby` cuando
  `tiene_ventas`. El motivo se define una vez para que tooltip y texto
  accesible no diverjan.
- Backend: el rechazo pasa de 400 a **409**, como se pidió.
- Commit `fb06b57`. Pruebas: 1 backend actualizada + 2 frontend.

### 13:05 — puerta de calidad del BLOQUE B

| Puerta | Resultado |
|---|---|
| Backend `manage.py test` | **656 OK** (línea base `main`: 627) |
| `ruff check` | limpio |
| `npm run lint` | limpio |
| `npm run test:ci` | **113 OK** (línea base: 103) |
| `npx ng build` | correcto |

`docs/PR-BODY-fase-4.md` escrito, con los cambios de contrato del API.

**BUG-14 no se tocó** (Fase 1 del compañero), como se indicó. No se revisó, así
que no hay nada que reportar sobre él.

---

## BLOQUE C — BUG-20: detalle de venta

### 13:20 — inicio

Rama `fix/qa-bug-20-detalle-venta` creada desde `main` (`3cc5879`).

### 14:10 — BUG-20 — HECHO

Hallazgo: el backend **ya estaba bien**. `VentaLecturaSerializer` y
`DetalleVentaLecturaSerializer` ya traían todos los campos pedidos, y
`VentaDetalleView.get` ya filtraba por empresa. No hizo falta tocar el
serializer, así que el bloque no cambia ningún contrato del API.

- Backend: solo pruebas que **fijan** el aislamiento (404 para una venta de
  otra empresa, verificado en los dos sentidos) y la forma de las líneas.
- Frontend: ruta `/ventas/:id`, encabezado, tabla de líneas y totales tal cual
  vienen del API, `TODO(BUG-21)` donde irá el IVA.
- Fila del listado clicable con ratón y con Enter (`tabindex`, `role="link"`,
  `aria-label`); «Anular» detiene la propagación.
- Imprimir con `@media print`: carta y ticket de 80 mm, sin librería de PDF.
- Commit `4fda51d`. Pruebas: 6 backend + 7 frontend.

Verificado que no se tocó nada del alcance vetado: `core/signals.py`,
`recalcular_totales_venta`, `views_tienda.py`, modelos `Venta`/`DetalleVenta`,
semillas. Sin migraciones.

### 14:15 — puerta de calidad del BLOQUE C

| Puerta | Resultado |
|---|---|
| Backend `manage.py test` | **633 OK** (línea base `main`: 627) |
| `ruff check` | limpio |
| `npm run lint` | limpio |
| `npm run test:ci` | **110 OK** (línea base: 103) |
| `npx ng build` | correcto |

`docs/PR-BODY-bug-20.md` escrito.

---

# Resumen para Dani

Los tres bloques terminados. **Nada bloqueado, nada sin commitear, sin push.**

## Tabla de bugs

| BUG | Rama | Commit | Estado | Prueba |
|---|---|---|---|---|
| Fase 2 (cierre) | `fix/qa-fase-2-seguridad` | `6ff8bd2` | Lista para PR | 691 backend OK |
| BUG-01 imágenes | `fix/qa-fase-4-productos` | `79b7e09` | Hecho | 5 backend + 1 frontend |
| BUG-02 paginación | `fix/qa-fase-4-productos` | `7e7934e` | Hecho | 14 backend + 3 frontend |
| BUG-24 inventario | `fix/qa-fase-4-productos` | `c1c4585` | Hecho | 10 backend + 4 frontend |
| BUG-25 Eliminar | `fix/qa-fase-4-productos` | `fb06b57` | Hecho | 1 backend + 2 frontend |
| BUG-20 detalle venta | `fix/qa-bug-20-detalle-venta` | `4fda51d` | Hecho | 6 backend + 7 frontend |
| BUG-14 modal | — | — | **No tocado** (Fase 1 de tu compañero) | — |

Cada bug se verificó fallando antes del arreglo.

## Puertas de calidad

| Bloque | Backend tests | ruff | lint | test:ci | ng build |
|---|---|---|---|---|---|
| A (Fase 2) | 691 OK | limpio | — | — | — |
| B (Fase 4) | 656 OK | limpio | limpio | 113 OK | OK |
| C (BUG-20) | 633 OK | limpio | limpio | 110 OK | OK |

Línea base en `main` antes de empezar: **627 backend, 103 frontend**, todo en
verde. No había fallos previos que heredar.

Los totales de B y C difieren porque son ramas distintas desde `main`, cada una
con sus propias pruebas.

## Decisiones tomadas sin Dani

1. **`DELETE /api/productos/` con ventas: 400 → 409.** Lo pediste explícitamente.
   Cambia el *status*, no el código ni el cuerpo, y el frontend ya ramificaba
   por código. *Alternativa descartada:* dejar el 400 y documentar la
   discrepancia, pero el 409 es lo correcto (lo impide el estado del recurso,
   no un error en la petición).

2. **Orden `(nombre, id)` también en el catálogo público.** No se pidió, pero
   sin desempate MySQL puede repetir una fila en dos páginas y omitir otra al
   paginar. No es observable salvo por dejar de perder filas. *Alternativa
   descartada:* tocar solo el panel y dejar el catálogo con el mismo defecto
   latente.

3. **El catálogo público no acepta `limite`.** Al reutilizar el helper habría
   sido gratis pasárselo entero, pero eso es superficie de API nueva en un
   endpoint público. Se le pasa solo `pagina` y hay una prueba que fija el
   contrato. *Alternativa descartada:* pasar los `query_params` completos.

4. **Los totales del detalle de venta se pintan tal cual llegan del API.**
   *Alternativa descartada:* recalcular subtotales en el cliente, que abriría la
   puerta a que pantalla y factura difieran por un redondeo.

5. **404 y no 403 para una venta de otra empresa.** Es lo que ya hacía el
   backend; se fijó con prueba en vez de cambiarlo. Un 403 confirmaría que el id
   existe en otro tenant.

6. **BUG-01 y BUG-02 en commits separados** aunque tocan los mismos tres
   archivos. Costó un ida y vuelta de edición quirúrgica; se hizo porque pediste
   un commit por bug.

## Hallazgos nuevos

1. **`Producto.imagen` también faltaba en inventario.** Se añadió al reutilizar
   el helper del BUG-01; no estaba en el alcance del ticket.

2. **`/api/inventario/productos/` hacía una consulta por fila** para el nombre
   de la categoría. Resuelto con `select_related('categoria')`.

3. **La rama de Fase 4 se creó por error desde `fix/qa-fase-2-seguridad`.** Se
   borró y se recreó desde `main` antes de cualquier cambio. Efecto colateral:
   el commit `6ff8bd2` de la Fase 2 arrastra una versión temprana de esta
   bitácora. Es inocuo, pero si te molesta en el PR, avísame.

4. **El separador de miles en las pruebas de frontend es el del locale por
   omisión (`,`), no el de `es-CO` (`.`).** El `LOCALE_ID` no está configurado
   en el `TestBed`. Las aserciones se escribieron tolerantes a ambos; si quieres
   que las pruebas reflejen el formato real hay que registrar el locale.

5. **BUG-14 no se revisó** en absoluto, como pediste. No puedo decir si está
   roto.

## Qué revisar primero al volver

1. **El cambio de significado de `total`** en `/api/productos/` y
   `/api/inventario/productos/`: antes era el tamaño de la página, ahora son los
   registros reales. Cualquier consumidor externo que lo usara ya mostraba un
   dato equivocado, pero conviene confirmar que no hay otro cliente.

2. **El 409 del DELETE de productos**, por si algún integrador chequea el 400.

3. **Los tres cuerpos de PR**: `docs/PR-BODY-fase-2.md`,
   `docs/PR-BODY-fase-4.md` y `docs/PR-BODY-bug-20.md`. Ninguna rama tiene push.

4. **El `TODO(BUG-21)`** en `venta-detalle.component.html`, para que encaje con
   lo que haga tu compañero con el IVA.

5. **La impresión en papel real.** El ticket de 80 mm se basa en `@media print
   and (max-width: 80mm)`, que es lo que declara una térmica de punto de venta,
   pero no pude probarlo contra una impresora física.

## Estado del entorno

- MySQL de Laragon **apagado** al terminar.
- Las tres ramas locales, sin push: `fix/qa-fase-2-seguridad` (10 commits),
  `fix/qa-fase-4-productos` (5), `fix/qa-bug-20-detalle-venta` (2).
- `backend/.env` no se tocó. No se ejecutó `seed_demo` ni `flush`. No se borró
  nada de `intersoft1_db`.
