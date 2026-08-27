"""Fase 7: vistas SQL de analitica (dashboard y reportes ADMINISTRADOR).

El caso de uso original menciona MongoDB para las agregaciones, pero este
proyecto usa MySQL. Se resuelve con vistas SQL materializadas en la base de
datos (equivalente a las agregaciones de MongoDB). Cada vista incluye
`empresa_id` para respetar el multi-tenancy por Foreign Key: los reportes de
una empresa nunca ven datos de otra (se filtra por empresa en las consultas).

Las tablas se nombran con la convencion Django `core_<modelo>` (ningun modelo
de core declara db_table propio).

Nombre de columnas en DB MySQL:
- Venta:          core_venta          (id, empresa_id, cliente_id, fecha, total,
                                        estado, deleted_at)
- DetalleVenta:   core_detalleventa   (id, venta_id, producto_id, cantidad,
                                        precio_unitario)
- Producto:       core_producto       (id, empresa_id, categoria_id, nombre, sku,
                                        precio, stock, stock_minimo, activo, deleted_at)
- Categoria:      core_categoria      (id, empresa_id, nombre)
- Cliente:        core_cliente        (id, empresa_id, tipo_documento,
                                        numero_documento, nombre)
- MovInventario:  core_movimientoinventario (id, producto_id, tipo, cantidad)
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_facturaelectronica_notacredito'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[

                # Ventas por dia (netas, solo completadas), por empresa y categoria.
                "CREATE VIEW vw_ventas_diarias AS "
                "SELECT v.empresa_id, "
                "       DATE(v.fecha) AS dia, "
                "       p.categoria_id, "
                "       COALESCE(c.nombre, 'Sin categoria') AS categoria, "
                "       COUNT(DISTINCT v.id) AS num_ventas, "
                "       COALESCE(SUM(dv.cantidad), 0) AS unidades, "
                "       COALESCE(SUM(dv.precio_unitario * dv.cantidad), 0) AS ingresos "
                "FROM core_venta v "
                "JOIN core_detalleventa dv ON dv.venta_id = v.id "
                "JOIN core_producto p ON p.id = dv.producto_id "
                "LEFT JOIN core_categoria c ON c.id = p.categoria_id "
                "WHERE v.deleted_at IS NULL AND v.estado = 'completada' "
                "GROUP BY v.empresa_id, DATE(v.fecha), p.categoria_id, "
                "         COALESCE(c.nombre, 'Sin categoria')",

                # Ventas por mes.
                "CREATE VIEW vw_ventas_mensuales AS "
                "SELECT v.empresa_id, "
                "       DATE_FORMAT(v.fecha, '%Y-%m') AS mes, "
                "       YEAR(v.fecha) AS anio, "
                "       MONTH(v.fecha) AS mes_numero, "
                "       p.categoria_id, "
                "       COALESCE(c.nombre, 'Sin categoria') AS categoria, "
                "       COUNT(DISTINCT v.id) AS num_ventas, "
                "       COALESCE(SUM(dv.cantidad), 0) AS unidades, "
                "       COALESCE(SUM(dv.precio_unitario * dv.cantidad), 0) AS ingresos "
                "FROM core_venta v "
                "JOIN core_detalleventa dv ON dv.venta_id = v.id "
                "JOIN core_producto p ON p.id = dv.producto_id "
                "LEFT JOIN core_categoria c ON c.id = p.categoria_id "
                "WHERE v.deleted_at IS NULL AND v.estado = 'completada' "
                "GROUP BY v.empresa_id, DATE_FORMAT(v.fecha, '%Y-%m'), "
                "         YEAR(v.fecha), MONTH(v.fecha), p.categoria_id, "
                "         COALESCE(c.nombre, 'Sin categoria')",

                # Top productos por unidades vendidas e ingresos.
                "CREATE VIEW vw_top_productos AS "
                "SELECT v.empresa_id, "
                "       dv.producto_id, "
                "       p.nombre AS producto, "
                "       p.sku, "
                "       p.categoria_id, "
                "       COALESCE(c.nombre, 'Sin categoria') AS categoria, "
                "       COALESCE(SUM(dv.cantidad), 0) AS unidades, "
                "       COALESCE(SUM(dv.precio_unitario * dv.cantidad), 0) AS ingresos "
                "FROM core_detalleventa dv "
                "JOIN core_venta v ON v.id = dv.venta_id "
                "JOIN core_producto p ON p.id = dv.producto_id "
                "LEFT JOIN core_categoria c ON c.id = p.categoria_id "
                "WHERE v.deleted_at IS NULL AND v.estado = 'completada' "
                "GROUP BY v.empresa_id, dv.producto_id, p.nombre, p.sku, "
                "         p.categoria_id, COALESCE(c.nombre, 'Sin categoria')",

                # Clientes frecuentes: numero de ventas y total comprado.
                "CREATE VIEW vw_clientes_frecuentes AS "
                "SELECT v.empresa_id, "
                "       cl.id AS cliente_id, "
                "       cl.nombre AS cliente, "
                "       cl.tipo_documento, "
                "       cl.numero_documento, "
                "       COUNT(DISTINCT v.id) AS num_ventas, "
                "       COALESCE(SUM(v.total), 0) AS total_comprado "
                "FROM core_venta v "
                "JOIN core_cliente cl ON cl.id = v.cliente_id "
                "WHERE v.deleted_at IS NULL AND v.estado = 'completada' "
                "GROUP BY v.empresa_id, cl.id, cl.nombre, cl.tipo_documento, "
                "         cl.numero_documento",

                # Valor de inventario por categoria (productos activos).
                "CREATE VIEW vw_valor_inventario AS "
                "SELECT p.empresa_id, "
                "       p.categoria_id, "
                "       COALESCE(c.nombre, 'Sin categoria') AS categoria, "
                "       COUNT(*) AS num_productos, "
                "       COALESCE(SUM(p.stock), 0) AS unidades, "
                "       COALESCE(SUM(p.precio * p.stock), 0) AS valor "
                "FROM core_producto p "
                "LEFT JOIN core_categoria c ON c.id = p.categoria_id "
                "WHERE p.deleted_at IS NULL AND p.activo = 1 "
                "GROUP BY p.empresa_id, p.categoria_id, "
                "         COALESCE(c.nombre, 'Sin categoria')",

                # Rotacion de inventario por producto: salidas / stock actual.
                "CREATE VIEW vw_rotacion AS "
                "SELECT p.empresa_id, "
                "       p.id AS producto_id, "
                "       p.nombre AS producto, "
                "       p.sku, "
                "       p.categoria_id, "
                "       COALESCE(c.nombre, 'Sin categoria') AS categoria, "
                "       COALESCE(SUM(CASE WHEN mi.tipo = 'salida' "
                "                          THEN mi.cantidad ELSE 0 END), 0) AS salidas, "
                "       p.stock AS stock_actual, "
                "       CASE WHEN p.stock = 0 THEN 0 "
                "            ELSE COALESCE(SUM(CASE WHEN mi.tipo = 'salida' "
                "                          THEN mi.cantidad ELSE 0 END), 0) / p.stock "
                "       END AS rotacion "
                "FROM core_producto p "
                "LEFT JOIN core_categoria c ON c.id = p.categoria_id "
                "LEFT JOIN core_movimientoinventario mi "
                "       ON mi.producto_id = p.id AND mi.tipo = 'salida' "
                "WHERE p.deleted_at IS NULL "
                "GROUP BY p.empresa_id, p.id, p.nombre, p.sku, p.categoria_id, "
                "         COALESCE(c.nombre, 'Sin categoria'), p.stock",

                # Productos bajo su stock minimo (activos, generan alerta).
                "CREATE VIEW vw_productos_bajo_minimo AS "
                "SELECT p.id AS producto_id, "
                "       p.empresa_id, "
                "       p.nombre AS producto, "
                "       p.sku, "
                "       p.categoria_id, "
                "       COALESCE(c.nombre, 'Sin categoria') AS categoria, "
                "       p.stock, "
                "       p.stock_minimo "
                "FROM core_producto p "
                "LEFT JOIN core_categoria c ON c.id = p.categoria_id "
                "WHERE p.deleted_at IS NULL AND p.activo = 1 "
                "  AND p.stock <= p.stock_minimo",
            ],
            reverse_sql=[
                "DROP VIEW IF EXISTS vw_ventas_diarias",
                "DROP VIEW IF EXISTS vw_ventas_mensuales",
                "DROP VIEW IF EXISTS vw_top_productos",
                "DROP VIEW IF EXISTS vw_clientes_frecuentes",
                "DROP VIEW IF EXISTS vw_valor_inventario",
                "DROP VIEW IF EXISTS vw_rotacion",
                "DROP VIEW IF EXISTS vw_productos_bajo_minimo",
            ],
        ),
    ]
