# Panel administrativo InterSoft — Guía para replicar en Figma

Extiende el paquete de diseño del marketplace (`figma-guide.md`) con el **panel
interno de administración**: capturas reales de la SPA en **desktop (1440×1000)**
y dos pantallas en **móvil (375×812)**, con sesión `ADMINISTRADOR`.

## 1. Capturas (carpeta `capturas-admin/`)

| Archivo | Ruta | Pantalla | Contenido demostrado |
|---------|------|----------|----------------------|
| `01-dashboard.png` | `/dashboard` | Panel | Tarjetas de métricas, tabla de ventas recientes, caché de negocio invalidado por generación. |
| `02-pos.png` | `/pos` | Punto de Venta | Búsqueda por SKU, carrito de mostrador, botón de confirmación de venta. |
| `03-ventas.png` | `/ventas` | Ventas | Historial de ventas POS y marketplace con totales y estados. |
| `04-envios.png` | `/envios` | Envíos | Cola de despachos filtrable por estado (`pendiente/preparando/despachado/...`). |
| `05-clientes.png` | `/clientes` | Clientes | CRUD de clientes con búsqueda y estados vacíos/error reutilizables. |
| `06-empleados.png` | `/empleados` | Empleados | Gestión de personal con permisos finos (requiere `empleado.leer`). |
| `07-productos.png` | `/productos` | Catálogo de productos | Listado con búsqueda, filtro y "Sin resultados" con acción limpiar filtros. |
| `08-inventario.png` | `/inventario` | Inventario | Movimientos y ajustes de stock (locks `select_for_update`). |
| `09-alertas.png` | `/alertas` | Alertas | Notificaciones de stock bajo, rol vs notificación. |
| `10-facturacion.png` | `/facturacion` | Facturación DIAN | Comprobantes electrónicos, notas crédito, estado DIAN. |
| `11-asistente-ia.png` | `/ia` | Asistente IA | Chat con contexto de negocio, rate-limit por usuario. |
| `12-usuarios.png` | `/admin/usuarios` | Usuarios (solo admin) | Alta de usuario, cambio de password, rol por empresa. |
| `13-roles.png` | `/admin/roles` | Roles y permisos | Permisos gruesos + finos, roles base no renombrables. |
| `14-reportes.png` | `/reportes` | Reportes | Filtros de fecha y agregados por empresa. |
| `15-camaras.png` | `/monitoreo/camaras` | Cámaras | Listado de cámaras + catálogo de grabaciones paginado (`sincronizar_grabaciones`). |
| `16-notificaciones.png` | `/monitoreo/notificaciones` | Notificaciones | Canales y plantillas de notificación. |
| `17-configuracion.png` | `/configuracion` | Configuración | Perfil/empresa y ajustes de la cuenta. |

### Versión móvil (375×812)
| Archivo | Pantalla |
|---------|----------|
| `m-dashboard.png` | Panel responsive con drawer de navegación |
| `m-ventas.png` | Ventas responsive |

Las capturas se regeneran con el script `frontend/scripts/capturas-figma-admin.mjs`
(requiere backend en `127.0.0.1:8000` y `ng serve` en `127.0.0.1:4200`, login
`ADMINISTRADOR`).

## 2. Design tokens

Mismos tokens del marketplace (una sola fuente de verdad): colores claro/noche,
escala `--e1..--e8`, radios (tarjeta 10 / botón 8 / card 12 / píldora 999),
sombras global y dropdown, tipografía `--fuente`. Ver `docs/DESIGN_SYSTEM.md`
y `tokens.json`.

## 3. Componentes a construir en Figma (repeatable)

1. **Sidebar de panel** — colapsable, ítems con icono 20px SVG `stroke`, estados
   `activo`/hover, botón "Contraer", drawer móvil con fondo oscurecido.
2. **Tira de métricas (dashboard)** — atas de tarjetas con valor `| number`
   es-CO y delta.
3. **Tabla de datos** — fila hover (`--fila-hover`), badges de estado,
   subtotales alineados a la derecha, acciones por fila.
4. **Badge de estado** — píldora semántica (ok/alerta/error) reutilizada en
   ventas, envíos y facturación.
5. **Modal + formulario** — caja blanca 10px radius, inputs con foco
   `--primario-suave`, mensajes `role="alert"`, botón deshabilitado mientras
   `guardando`.
6. **Paginador** — `.paginador` centrado con separador superior, "Página X de Y".
7. **Cola de envíos** — lista filtrable por estado con transiciones válidas
   (modal para transportadora/guía/fecha/notas).
8. **Listado de cámaras + grabaciones** — tarjeta de cámara (imagen `url_stream`
   en apertura nueva) y catálogo paginado con `disponible`/`solo-archivo` y
   reproducción.
9. **Chat de IA** — burbujas asistente/usuario con rate-limit y estados de
   carga.
10. **Estados vacíos / error** — `app-estado-vacio` con variantes
    `vacio|busqueda|error` y botón "Reintentar".

## 4. Navegación (flujo del panel)

```
/login ──▶ /dashboard ──▶ sidebar ──▶ POS, Ventas, Envíos, Clientes,
    Empleados, Productos, Inventario, Alertas, Facturación, IA,
    Usuarios/Roles (admin), Reportes, Cámaras, Notificaciones, Configuración
```