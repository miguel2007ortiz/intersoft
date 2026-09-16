# QA Fase 4 — productos e inventario

Cierra BUG-01, BUG-02, BUG-24 y BUG-25. Rama `fix/qa-fase-4-productos`, 4
commits desde `main`.

El principio de la fase: `/api/tienda/catalogo/` ya resolvía bien imágenes y
paginación. En vez de reimplementarlo, se extrajo su patrón a dos módulos
compartidos y se aplicó al panel.

## Resumen por bug

### BUG-01 — imágenes rotas en el panel

`/api/productos/` devolvía `"/media/..."` relativa y el catálogo devolvía la
absoluta. El `ImageField` de DRF solo construye la absoluta si el `request`
está en el contexto del serializer: el catálogo lo pasaba, el panel no. En
desarrollo el panel se sirve desde otro origen que la API, así que esa ruta
relativa apuntaba al servidor de Angular y la miniatura salía rota.

- Nuevo `core/serializers_base.py` con `ImagenAbsolutaMixin`, que resuelve
  `imagen` con `request.build_absolute_uri()` de forma explícita. Lo usan los
  dos serializers de producto, así que la regla vive en un solo sitio y no
  depende de que alguien recuerde pasar el `request`.
- Las cuatro respuestas del panel (listado, detalle, creación, edición) pasan
  el `request` en el contexto.
- Frontend: `loading="lazy"` en la miniatura —la tabla puede traer 200 filas— y
  respaldo en `(error)` si el archivo ya no está en disco, en vez de dejar el
  icono de imagen rota. El respaldo es un SVG en *data URI*: no añade una
  petición ni un archivo que se pueda perder al desplegar, que es justo el
  fallo del que protege.

### BUG-02 — imposible pasar del producto 50 de 1.024

El listado cortaba con `[:limite]` y devolvía `total = len(datos)`, es decir el
tamaño de la página y no los registros que cumplían el filtro. No había forma
de saber que había más ni de pedir la siguiente.

- Nuevo `core/paginacion.py`: `COUNT(*)` sobre el filtro antes de recortar,
  parámetro `pagina`, techo de 200 filas y contadores `desde`/`hasta`.
- Orden `(nombre, id)`. **El desempate no es cosmético**: con nombres repetidos
  y un orden ambiguo MySQL puede devolver la misma fila en dos páginas y omitir
  otra — es el registro que «desaparece» al pasar de página.
- Frontend: componente compartido `app-paginador` con «Mostrando X–Y de N». La
  búsqueda y los filtros viajan en cada petición, así que cambiar de página no
  los pierde; y buscar o filtrar vuelve a la página 1, porque seguir en la
  página 7 de un conjunto nuevo deja la tabla vacía sin explicación.

### BUG-24 — inventario sin buscador ni paginación

Mismo problema del BUG-02 en otra pantalla. El buscador con *debounce* de
300 ms ya existía; faltaba la paginación y que los filtros se combinaran bien.

- `/api/inventario/productos/` usa el mismo `core/paginacion.py`.
- **Los dos filtros se combinan en el servidor.** Es lo que se rompía: aplicar
  «solo stock bajo» sobre la página ya recortada habría mirado únicamente los
  50 primeros productos por nombre.
- `select_related('categoria')`: la fila muestra el nombre de la categoría y
  antes costaba una consulta por producto.
- La fila incluye `imagen` absoluta, reutilizando el helper del BUG-01.

### BUG-25 — «Eliminar» aparecía y desaparecía

El botón solo se pintaba cuando `tiene_ventas` era falso. Aparecer y
desaparecer según la fila hacía pensar que la acción fallaba o que la tabla
estaba mal, y no explicaba nada.

- El botón se muestra siempre; con ventas asociadas queda deshabilitado, con
  `title` para el ratón y `aria-describedby` apuntando a un texto real para el
  lector de pantalla, que **no** anuncia los `title`. El motivo se define una
  sola vez en el componente para que las dos vías no diverjan.
- El backend ya lo impedía; ahora responde **409** en vez de 400.

## Cambios de contrato del API de productos

### `GET /api/productos/` e `GET /api/inventario/productos/`

`total` **cambia de significado**: antes era el número de filas devueltas, ahora
es el número de registros que cumplen el filtro. Cualquier cliente que lo usara
para pintar «N productos» ya estaba mostrando un dato equivocado.

Claves nuevas en la respuesta (aditivas):

| Clave | Qué es |
|---|---|
| `pagina` | Página devuelta (1-based) |
| `por_pagina` | Filas por página (tope 200) |
| `total_paginas` | Páginas que cubren el filtro |
| `desde` / `hasta` | Primer y último registro de esta página (1-based). `0` si está vacía |

Parámetros nuevos: `pagina` (por omisión 1; un valor inválido cae en 1) y
`limite` (por omisión 50, máximo 200; `limite=100000` se recorta a 200).

`imagen` pasa de ruta relativa a **URL absoluta** en todas las respuestas de
producto del panel. `null` si el producto no tiene imagen.

`/api/inventario/productos/` gana además el campo `imagen`.

### `DELETE /api/productos/<id>/` con ventas asociadas

`400` → **`409 Conflict`**. El código `PRODUCTO_CON_VENTAS` y el cuerpo no
cambian, y el frontend ya ramificaba por código y no por *status*.

### `GET /api/tienda/catalogo/` — sin cambios

Se refactorizó para usar el mismo helper, pero su contrato **no** cambia:
mismas claves, `por_pagina` sigue fijo en 24 y sigue sin aceptar `limite`. Hay
una prueba que fija ese contrato para que el refactor no lo erosione. Lo único
que gana es el desempate por `id` en el orden, que no es observable salvo por
dejar de perder filas al paginar.

## Verificación

| | |
|---|---|
| Backend `manage.py test` | **656 tests, OK** (línea base en `main`: 627) |
| `ruff check` | limpio |
| Frontend `npm run lint` | limpio (ESLint + Prettier) |
| Frontend `npm run test:ci` | **113 tests, OK** (línea base: 103) |
| `ng build` | correcto |

Pruebas nuevas: 29 en backend y 10 en frontend. Cada bug tiene una prueba que
se verificó fallando antes del arreglo.

## Nota

BUG-14 (validación del modal) queda **fuera de alcance** por indicación
explícita: es de la Fase 1 de otro compañero. No se tocó ni se revisó.
