# Core

Dominio de negocio de InterSoft (multi-tenant: todo cuelga de `Empresa`).

## Modelos
- `Empresa`: negocio del cliente (SaaS multi-tenant).
- `Categoria` / `Producto`: catalogo. Constraints: precio >= 0, stock >= 0,
  stock_minimo >= 0 (validacion global en base de datos).
- `Cliente`: directorio de clientes. Documento `(tipo, numero)` unico dentro de
  cada empresa; puede vincularse opcionalmente a una cuenta (`usuario`) para el
  portal del cliente.
- `Venta` / `DetalleVenta`: facturacion con lineas por producto. Estados:
  pendiente, completada, anulada. El numero de factura se autogenera.
- `MovimientoInventario`: kardex de entradas, salidas y ajustes de stock.
- `Notificacion`: avisos para los usuarios (p. ej. stock bajo).

Todos heredan de `TimeStampedModel`: UUID como PK, timestamps y borrado logico
(`deleted_at` + `soft_delete()`).

## Comandos
- `python manage.py seed_demo`: datos de demostracion (ejecuta `seed_roles`
  primero). Crea la empresa "Tienda El Progreso" con admin, empleado,
  productos, clientes y ventas.
