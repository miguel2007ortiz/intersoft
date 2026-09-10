# Marketplace InterSoft — Guía para replicar en Figma

Este paquete contiene las **capturas reales** del marketplace en **desktop (1440×1000)** y
**móvil (375×812)** y los **design tokens** del frontend, para reconstruir el diseño en Figma.

## 1. Capturas (carpeta `capturas/`)

| Archivo | Pantalla | Contenido demostrado |
|---------|----------|----------------------|
| `01-catalogo.png` | Catálogo | Hero/carousel + grid de tarjetas con imagen, badge Nuevo/stock, precio `COP`, corazón activo, carrito, menú hamburguesa. Sesión de comprador. |
| `01b-menu-abierto.png` | Catálogo (menú desplegado) | Menú hamburguesa: cabecera de usuario (Ana Torres · CLIENTE) + ítems (Mis favoritos, Mis pedidos, Salir) |
| `01c-modal-detalle.png` | Modal de detalle | Imagen grande, categoría/nombre/SKU, calificación con estrellas, precio `COP`, selector de cantidad, corazón, "Comprar ahora" |
| `02-carrito.png` | Carrito | Tabla con 2 items (Zapatos x1 $75.000, Camiseta Polo x2 $90.000), controles de cantidad, subtotal/descuento/total |
| `03-checkout.png` | Checkout | Resumen del pedido + resumen de totales + botón "Pagar" |
| `04-pedidos.png` | Mis pedidos | Historial: 2 pedidos (FT-00001 $75.000, FT-00002 $90.000) con detalles |
| `05-favoritos.png` | Mis favoritos | Grid de productos guardados con corazón para quitar |

### Versión móvil (375×812, deviceScaleFactor 2)
| Archivo | Pantalla |
|---------|----------|
| `m-catalogo.png` | Catálogo responsive (hero + grid apilado) |
| `m-catalogo-menu.png` | Menú hamburguesa desplegado en móvil |
| `m-carrito.png` | Carrito móvil |
| `m-checkout.png` | Checkout móvil |
| `m-pedidos.png` | Mis pedidos móvil |
| `m-favoritos.png` | Mis favoritos móvil |

## 2. Design tokens (fuente: `frontend/src/styles.css` + `catalogo.component.css`)

### Colores — modo claro
| Token | Hex | Uso en marketplace |
|-------|-----|--------------------|
| `--primario` | `#2657D9` | Botones (Agregar, Comprar ahora, Pagar), corazones activos, enlaces, ítem primario |
| `--primario-osc` | `#16326E` | Hover de enlaces de menú |
| `--primario-suave` | `#E9EFFC` | Hover de tarjetas/ítems, fondo de chip |
| `--tinta` | `#101828` | Texto principal (nombres, precios) |
| `--gris` | `#5B6472` | Texto secundario (categoría, rol, fechas) |
| `--linea` | `#DCE3EE` | Bordes de tarjeta, tablas, menú dropdown |
| `--papel` | `#F5F7FA` | Fondo de página |
| `--blanco` | `#FFFFFF` | Fondo de tarjetas, modal, menú |
| `--ok` | `#0F766E` | Badge disponible, confirmaciones |
| `--alerta` | `#A85B00` | Badge "Últimas unidades" |
| `--error` | `#B3261E` | Mensajes de error, badge sin stock |

### Espaciado (escala)
| Token | px |
|-------|----|
| `--e1` | 4 |
| `--e2` | 8 |
| `--e3` | 12 |
| `--e4` | 16 |
| `--e5` | 24 |
| `--e6` | 32 |
| `--e7` | 48 |
| `--e8` | 64 |

### Radios y sombras
- `--radio`: 10px
- Botón: 8px · Dropdown: 12px · Tarjeta: 10px
- Sombra global: `0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.05)`
- Dropdown menú: `0 16px 40px rgba(15,23,42,0.16)`

### Tipografía
- Font-family: `'Segoe UI', system-ui, -apple-system, Arial, sans-serif`
- Precio: `| number` con locale **es-CO** → formato `45.000 COP` (miles con punto, "COP" después)

## 3. Componentes a construir en Figma (repeatable)

1. **Tarjeta de producto** — imagen (400×300, corner 10), badge "Nuevo"/"Últimas" (corregido a la derecha, sin solaparse con el corazón), categoría, nombre (14px), calificación (estrellas `★`/`☆`), SKU, precio `COP`, botón "Agregar", corazón activo. Variante: hover.
2. **Botón primario** — fondo `#2657D9`, texto blanco, radio 8px, alineación central. Variantes: default/hover/loading ("Agregando...")/ok (check).
3. **Badge Nuevo/stock** — fondo `$--ok`/`$--alerta`, punta redondeada.
4. **Menú hamburguesa** — botón 42×42 (icono 3 líneas de 2px), dropdown 220px+ con cabecera de usuario + ítems con icono (17px).
5. **Modal de detalle** — fondo con blur, caja blanca 12px radius, imagen grande, selector de cantidad (1..stock), corazón, "Comprar ahora".
6. **Estrellas** — `★` llenas + `☆` vacías, 5 posiciones; color `--alerta`.
7. **Fila de carrito/número** — tabla con subtotales alineados a la derecha.
8. **Resumen de totales** — filas Subtotal/Descuento/Total, total en negrita con borde superior.

## 4. Navegación entre pantallas (flujo)

```
/catalogo ──click tarjeta──▶ 01c-modal-detalle
    │
    └──hamburguesa──▶ 01b-menu-abierto
    └──carrito──────▶ 02-carrito ──"Pagar"──▶ 03-checkout ──"Pagar"──▶ (pedido)
    └──Mis favoritos▶ 05-favoritos
    └──Mis pedidos──▶ 04-pedidos
```