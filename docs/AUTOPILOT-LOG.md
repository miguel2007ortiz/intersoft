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
