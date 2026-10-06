"""Volumen de datos: indices de apoyo a las agregaciones del dashboard.

El dashboard y los reportes se resuelven con vistas SQL (`vw_*`, migracion
0006) que agregan el historico completo sobre las tablas base. La tarea de
volumen anade indices compuestos aditivos (migracion 0025) para que esas
agregaciones no recorran tablas enteras:

- `detventa_prod_venta_idx`  -> vw_top_productos (agrega por producto).
- `mov_prod_tipo_idx`        -> vw_rotacion (solo salidas por producto).
- `prod_emp_activo_cat_idx`  -> vw_valor_inventario y vw_productos_bajo_minimo.

Este modulo verifica que los indices existen en el esquema real de la BD de
prueba (no solo en el modelo), para que no se pierdan en un futuro refactor
de migraciones.
"""

from django.db import connection
from django.test import TestCase


class IndicesAnaliticaTest(TestCase):
    """Regresion: los indices de soporte a las vistas deben existir."""

    INDICES_ESPERADOS = {
        'core_detalleventa': {'detventa_prod_venta_idx'},
        'core_movimientoinventario': {'mov_prod_tipo_idx'},
        'core_producto': {'prod_emp_activo_cat_idx'},
    }

    def _indices_tabla(self, tabla):
        """Devuelve el set de nombres de indices existentes en la tabla."""
        restricciones = connection.introspection.get_constraints(
            connection.cursor(), tabla)
        return {nombre for nombre, detalle in restricciones.items()
                if not detalle.get('unique')}

    def test_los_indices_de_apoyo_existen(self):
        for tabla, indices in self.INDICES_ESPERADOS.items():
            with self.subTest(tabla=tabla):
                presentes = self._indices_tabla(tabla)
                self.assertEqual(indices - presentes, set(),
                                 f"Faltan indices en {tabla}: "
                                 f"{indices - presentes}")