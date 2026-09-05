# InterSoft — Design System vivo

> Documento de consulta del sistema de diseño del frontend (Angular). Los tokens
> aquí descritos se leen directamente de **`frontend/src/styles.css`** (fuente de
> verdad) y los componentes de la tienda de `catalogo.component.css`. Si un valor
> cambia en el CSS, esta tabla queda desactualizada: por eso se llama "vivo" —
> el CSS manda.

Las capturas reales del marketplace (desktop 1440×1000 y móvil 375×812) y los
tokens exportables a Figma están en **`figma-marketplace/`** (`tokens.json` y
`capturas/`). Esa carpeta es un artefacto externo de diseño y **no se versiona**
en el repo.

---

## 1. Colores — modo claro (tema por defecto)

| Token | Hex | Uso |
|-------|-----|-----|
| `--primario` | `#2657d9` | Botones primarios, enlaces, corazones activos |
| `--primario-osc` | `#16326e` | Hover de enlaces, `--btn-fin` del botón |
| `--primario-suave` | `#e9effc` | Hover de tarjetas, fondo de foco de inputs |
| `--tinta` | `#101828` | Texto principal |
| `--gris` | `#5b6472` | Texto secundario (categorías, fechas, roles) |
| `--linea` | `#dce3ee` | Bordes de tarjeta/tabla/menú |
| `--papel` | `#f5f7fa` | Fondo de página |
| `--blanco` | `#ffffff` | Fondo de tarjetas, modal, menú |
| `--error` | `#b3261e` | Errores, badge sin stock |
| `--alerta` | `#a85b00` | Badge "Últimas unidades" |
| `--ok` | `#0f766e` | Badge disponible, confirmaciones |

### Términos semánticos (modo claro)
| Token | Hex | Uso |
|-------|-----|-----|
| `--tarjeta` | `#ffffff` | Fondo de superficie (tarjetas) |
| `--btn-fin` | `#16326e` | Fin del gradiente del botón primario |
| `--barra-fondo` | `rgba(255,255,255,0.82)` | Barra de navegación (transparente) |
| `--fila-hover` | `#f3f7ff` | Hover de filas de tabla |
| `--chip-fondo` | `#f1f5fd` | Fondo de chips/categorías |
| `--ok-fondo` / `--ok-borde` | `#e6f5f3` / `#b9e4df` | Aviso/success |
| `--error-fondo` / `--error-borde` | `#fbebea` / `#f3c9c6` | Aviso de error |
| `--alerta-fondo` / `--alerta-borde` | `#fbf1e3` / `#efd9b4` | Aviso de advertencia |

## 2. Colores — modo noche

Se activa con la clase `body.noche` (fase 3). Reasigna los tokens base:

| Token | Claro | Noche |
|-------|-------|-------|
| `--primario` | `#2657d9` | `#5b82ff` |
| `--primario-osc` | `#16326e` | `#a6bcff` |
| `--primario-suave` | `#e9effc` | `#17233f` |
| `--tinta` | `#101828` | `#e7ecf6` |
| `--gris` | `#5b6472` | `#96a2b8` |
| `--linea` | `#dce3ee` | `#27334d` |
| `--papel` | `#f5f7fa` | `#0b1220` |
| `--blanco` | `#ffffff` | `#121b2e` |
| `--sombra` | claro | `0 1px 3px rgba(0,0,0,0.4), 0 10px 28px rgba(0,0,0,0.35)` |

## 3. Escala de espaciado

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

## 4. Radios y sombras

- Tarjeta general `--radio`: **10px** · Botón: **8px** · Tarjeta de producto `.card`: **12px**
- Badge/chip (píldora): **999px**
- Sombra global `--sombra`: `0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.05)`
- Sombra dropdown (menú hamburguesa, `#16326e` shadow): `0 16px 40px rgba(15,23,42,0.16)`

## 5. Tipografía

- Fuente `--fuente`: `'Segoe UI', system-ui, -apple-system, Arial, sans-serif`
- Cuerpo: 14px / peso 500, line-height 1.6 (global)
- Títulos de tarjeta/marketplace: 16px / peso 600
- Precio: `| number` con locale **es-CO** → `45.000 COP` (miles con punto, "COP" después)
- Botones: peso 600, foco visible con anillo `--primario-suave`

## 6. Componentes reutilizables

Definidos en `styles.css` (globales) y `catalogo.component.css` (tienda):

| Componente | Clase(s) | Notas |
|------------|----------|-------|
| Botón primario | `.btn.btn-primario` | Gradiente `--primario`→`--btn-fin`, brillo al hover, radio 8px |
| Botón secundario | `.btn.btn-secundario` | Borde `--linea`, hover `--primario-suave` |
| Chip / categoría | `.chip`, `.chip-activo` | Píldora 999px, cuenta con `.chip-cuenta` |
| Tarjeta genérica | `.tarjeta`, `.card` | `.tarjeta`=10px, `.card`=12px con `.card-img`/`.card-body` |
| Badge | `.badge`, `.badge-urgencia` | Esquina superior, uppercase, píldora |
| Aviso | `.aviso-ok/-error/-alerta` | Fondo + borde + color semántico |
| Esqueleto de carga | `.skeleton`, `.skeleton-img`, `.skeleton-linea` | Placeholder con brillo animado |
| Paginador | `.paginador`, `.paginador-info`, `.btn-paginador` | Centrado, separador superior |
| Toast de éxito | `.exito-toast` | Fijo abajo-derecha, fondo `#067647` |
| Imagen producto | `.card-img` | Altura 160px, `object-fit: contain`, zoom al hover |
| Efecto flotar | `.tarjeta-flot` | `translateY(-4px)` + borde primario al hover |
| Entrada/revelado | `.aparecer`, `.por-revelar`/`.revelada` | Animación en cascada / por scroll (directiva `RevelarAlEntrar`) |

### Accesibilidad
- `prefers-reduced-motion: reduce` desactiva todas las animaciones decorativas.
- Foco visible documentado (`:focus-visible`, anillo 2px `--primario`).
- Textos secundarios con contraste sobre `--papel` verificado (gris `#5b6472` sobre `#f5f7fa`).

## 7. Exportación a Figma

`figma-marketplace/` contiene el paquete para reconstruir el diseño:
- `tokens.json` — design tokens (colores, spacing, radii, sombras, tipografía).
- `capturas/` — pantallas reales desktop + móvil (ver `figma-guide.md` para el detalle de cada una y los componentes a armar).
- `figma-guide.md` — instrucciones de replicado y navegación entre pantallas.
