"""Analitica de la fase 7 (dashboard y reportes, solo ADMINISTRADOR).

El caso de uso original plantea MongoDB para las agregaciones; este proyecto
usa MySQL, asi que *todas* las agregaciones se resuelven con vistas SQL
(ver core/migrations/0006_dashboard_vistas.py) que se consultan aqui,
filtrando siempre por empresa (multi-tenancy) y por rango de fechas/categoria
cuando aplica. Ningun dato se junta en Python; las vistas devuelven filas
listas para graficar o exportar.
"""

import csv
import io
import numbers
import uuid as uuid_mod
from datetime import datetime

from django.db import connection
from django.utils import timezone


class FiltrosDashboard:
    """Filtros comunes de fecha y categoria para las consultas de analitica."""

    def __init__(self, request):
        self.empresa_id = request.user.perfil.empresa_id
        self.fecha_inicio = request.query_params.get('fecha_inicio') or None
        self.fecha_fin = request.query_params.get('fecha_fin') or None
        self.categoria_id = request.query_params.get('categoria') or None
        self.limite = self._limite(
            request.query_params.get('limite', '100'))

    @staticmethod
    def _limite(valor):
        try:
            return max(1, min(int(valor), 500))
        except (TypeError, ValueError):
            return 100

    def ventas_where(self, alias_fecha='dia', alias_cat='categoria_id',
                     con_categoria=True):
        """Clausula WHERE para vistas de ventas (fila por dia/mes/producto).

        `con_categoria=False` se usa en vistas que no tienen la columna
        categoria_id (p. ej. clientes_frecuentes), donde el filtro por
        categoria simplemente se ignora.
        """
        partes = [f"empresa_id = %s"]
        params = [self.empresa_id]
        if self.fecha_inicio:
            partes.append(f"{alias_fecha} >= %s")
            params.append(self.fecha_inicio)
        if self.fecha_fin:
            partes.append(f"{alias_fecha} <= %s")
            params.append(self.fecha_fin)
        if con_categoria and self.categoria_id:
            partes.append(f"{alias_cat} = %s")
            params.append(self.categoria_id)
        return (' AND '.join(partes)), params


def _param_id(valor):
    """Normaliza un id (UUID o str) a la forma en que Django lo guarda en
    MySQL (char(32) sin guiones). Sin esta conversion, pasar un UUID de Python
    como parametro SQL no coincidiria con el valor almacenado."""
    if isinstance(valor, uuid_mod.UUID):
        return valor.hex
    return valor


def ejecutar(sql, params):
    """Ejecuta SQL y devuelve lista de dicts parametrizada (solo lectura)."""
    params = [_param_id(p) for p in (params or [])]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columnas = [d[0] for d in cursor.description]
        filas = cursor.fetchall()
    return [dict(zip(columnas, fila)) for fila in filas]


# ----------------------------- Dashboard ----------------------------------

def resumen(f):
    """KPIs del panel de control para el rango de fechas seleccionado."""
    where, params = f.ventas_where()

    # Ventas del rango
    ventas = ejecutar(
        f"SELECT COALESCE(SUM(ingresos),0) AS ingresos, "
        f"       COALESCE(SUM(num_ventas),0) AS num_ventas, "
        f"       COALESCE(SUM(unidades),0) AS unidades "
        f"FROM vw_ventas_diarias WHERE {where}", params + [])[0]

    # Valor del inventario (sin rango; es una foto actual)
    valor = ejecutar(
        "SELECT COALESCE(SUM(valor),0) AS valor_total, "
        "       COALESCE(SUM(unidades),0) AS unidades_total "
        "FROM vw_valor_inventario WHERE empresa_id = %s",
        [f.empresa_id])[0]

    # Productos bajo minimo
    bajo = ejecutar(
        "SELECT COUNT(*) AS cantidad "
        "FROM vw_productos_bajo_minimo WHERE empresa_id = %s",
        [f.empresa_id])[0]['cantidad']

    # Ticket promedio (solo completo, sin doble conteo de numerador)
    ticket = ejecutar(
        "SELECT CASE WHEN SUM(num_ventas)=0 THEN 0 "
        "            ELSE SUM(ingresos)/SUM(num_ventas) END AS ticket "
        f"FROM vw_ventas_diarias WHERE {where}", params)[0]['ticket']

    return {
        'empresa_id': f.empresa_id,
        'rango': {'fecha_inicio': f.fecha_inicio, 'fecha_fin': f.fecha_fin},
        'ingresos_totales': _num(ventas['ingresos']),
        'num_ventas': _num(ventas['num_ventas']),
        'unidades_vendidas': _num(ventas['unidades']),
        'ticket_promedio': _num(ticket),
        'valor_inventario': _num(valor['valor_total']),
        'unidades_inventario': _num(valor['unidades_total']),
        'productos_bajo_minimo': _num(bajo),
    }


def ventas_por_dia(f):
    """Series para la grafica de barras: ingresos y ventas por dia."""
    where, params = f.ventas_where()
    filas = ejecutar(
        f"SELECT dia, COALESCE(SUM(ingresos),0) AS ingresos, "
        f"       COALESCE(SUM(num_ventas),0) AS num_ventas "
        f"FROM vw_ventas_diarias WHERE {where} "
        f"GROUP BY dia ORDER BY dia", params)
    for fila in filas:
        fila['dia'] = fila['dia'].strftime('%Y-%m-%d')
        fila['ingresos'] = _num(fila['ingresos'])
    return filas


def ventas_por_mes(f):
    where, params = f.ventas_where('mes')
    filas = ejecutar(
        f"SELECT mes, COALESCE(SUM(ingresos),0) AS ingresos, "
        f"       COALESCE(SUM(num_ventas),0) AS num_ventas "
        f"FROM vw_ventas_mensuales WHERE {where} "
        f"GROUP BY mes ORDER BY mes", params)
    for fila in filas:
        fila['ingresos'] = _num(fila['ingresos'])
    return filas


def top_productos(f):
    where, params = f.ventas_where(alias_fecha='dia')
    filas = ejecutar(
        f"SELECT producto, sku, categoria, "
        f"       COALESCE(SUM(unidades),0) AS unidades, "
        f"       COALESCE(SUM(ingresos),0) AS ingresos "
        f"FROM vw_top_productos WHERE {where} "
        f"GROUP BY producto, sku, categoria "
        f"ORDER BY SUM(unidades) DESC LIMIT {f.limite}", params)
    for fila in filas:
        fila['ingresos'] = _num(fila['ingresos'])
    return filas


def clientes_frecuentes(f):
    """Top clientes por total comprado (historia acumulada de la vista)."""
    filas = ejecutar(
        "SELECT cliente, tipo_documento, numero_documento, "
        "       num_ventas, total_comprado "
        "FROM vw_clientes_frecuentes WHERE empresa_id = %s "
        "ORDER BY total_comprado DESC LIMIT %s",
        [f.empresa_id, f.limite])
    for fila in filas:
        fila['total_comprado'] = _num(fila['total_comprado'])
    return filas


def valor_inventario_por_categoria(empresa_id):
    return ejecutar(
        "SELECT categoria, num_productos, unidades, valor "
        "FROM vw_valor_inventario WHERE empresa_id = %s "
        "ORDER BY valor DESC", [empresa_id])


def rotacion_productos(empresa_id, limite=100):
    return ejecutar(
        "SELECT producto, sku, categoria, salidas, stock_actual, rotacion "
        "FROM vw_rotacion WHERE empresa_id = %s "
        "ORDER BY rotacion DESC LIMIT %s", [empresa_id, limite])


def productos_bajo_minimo(empresa_id):
    return ejecutar(
        "SELECT producto, sku, categoria, stock, stock_minimo "
        "FROM vw_productos_bajo_minimo WHERE empresa_id = %s "
        "ORDER BY (stock_minimo - stock) DESC", [empresa_id])


def categorias(empresa_id):
    """Catalogo de categorias para el filtro del dashboard/reportes."""
    return ejecutar(
        "SELECT id AS categoria_id, nombre AS categoria "
        "FROM core_categoria WHERE empresa_id = %s "
        "AND deleted_at IS NULL ORDER BY nombre", [empresa_id])


# ----------------------------- Reportes -----------------------------------

# Definicion de los tipos de reporte que consultan las vistas creadas.
TIPOS_REPORTE = {
    'ventas_diarias': {
        'titulo': 'Ventas por dia',
        'vista': 'vw_ventas_diarias',
        'categoria': True,
        'columnas': [('dia', 'Fecha'), ('categoria', 'Categoria'),
                     ('num_ventas', 'N. Ventas'), ('unidades', 'Unidades'),
                     ('ingresos', 'Ingresos')],
        'fecha': 'dia',
    },
    'ventas_mensuales': {
        'titulo': 'Ventas por mes',
        'vista': 'vw_ventas_mensuales',
        'categoria': True,
        'columnas': [('mes', 'Mes'), ('categoria', 'Categoria'),
                     ('num_ventas', 'N. Ventas'), ('unidades', 'Unidades'),
                     ('ingresos', 'Ingresos')],
        'fecha': 'mes',
    },
    'top_productos': {
        'titulo': 'Top productos',
        'vista': 'vw_top_productos',
        'categoria': True,
        'columnas': [('producto', 'Producto'), ('sku', 'SKU'),
                     ('categoria', 'Categoria'), ('unidades', 'Unidades'),
                     ('ingresos', 'Ingresos')],
        'fecha': 'dia',
    },
    'clientes_frecuentes': {
        'titulo': 'Clientes frecuentes',
        'vista': 'vw_clientes_frecuentes',
        'categoria': False,
        # La vista agrega el historico completo (no tiene columna de fecha),
        # asi que este reporte no filtra por rango; es una foto acumulada.
        'fecha': None,
        'columnas': [('cliente', 'Cliente'), ('numero_documento', 'Documento'),
                     ('num_ventas', 'N. Ventas'), ('total_comprado', 'Total')],
    },
    'valor_inventario': {
        'titulo': 'Valor de inventario',
        'vista': 'vw_valor_inventario',
        'categoria': True,
        'columnas': [('categoria', 'Categoria'), ('num_productos', 'Productos'),
                     ('unidades', 'Unidades'), ('valor', 'Valor')],
        'fecha': None,
    },
    'rotacion': {
        'titulo': 'Rotacion de inventario',
        'vista': 'vw_rotacion',
        'categoria': True,
        'columnas': [('producto', 'Producto'), ('sku', 'SKU'),
                     ('categoria', 'Categoria'), ('salidas', 'Salidas'),
                     ('stock_actual', 'Stock'), ('rotacion', 'Rotacion')],
        'fecha': None,
    },
    'productos_bajo_minimo': {
        'titulo': 'Productos bajo minimo',
        'vista': 'vw_productos_bajo_minimo',
        'categoria': True,
        'columnas': [('producto', 'Producto'), ('sku', 'SKU'),
                     ('categoria', 'Categoria'), ('stock', 'Stock'),
                     ('stock_minimo', 'Minimo')],
        'fecha': None,
    },
}


def reporte(tipo, f):
    """Consulta las filas de la vista solicitada aplicando empresa + filtros."""
    if tipo not in TIPOS_REPORTE:
        raise KeyError(tipo)
    def_reporte = TIPOS_REPORTE[tipo]
    vista = def_reporte['vista']
    alias_fecha = def_reporte['fecha']

    where = "empresa_id = %s"
    params = [f.empresa_id]
    # Solo se filtra por categoria en las vistas que la tienen declarada.
    if f.categoria_id and def_reporte.get('categoria', False):
        where += " AND categoria_id = %s"
        params.append(f.categoria_id)
    if alias_fecha:
        if f.fecha_inicio:
            where += f" AND {alias_fecha} >= %s"
            params.append(f.fecha_inicio)
        if f.fecha_fin:
            where += f" AND {alias_fecha} <= %s"
            params.append(f.fecha_fin)

    sql = f"SELECT * FROM {vista} WHERE {where}"
    if alias_fecha:
        sql += f" ORDER BY {alias_fecha}"
    filas = ejecutar(sql, params)
    return filas, def_reporte


def exportar_csv(tipo, f):
    """Genera un CSV UTF-8 (con BOM para abrir bien en Excel) del reporte."""
    filas, def_reporte = reporte(tipo, f)
    salida = io.StringIO()
    escritor = csv.writer(salida)

    escritor.writerow([def_reporte['titulo']])
    escritor.writerow(['Generado', timezone.localtime().strftime('%Y-%m-%d %H:%M')])
    escritor.writerow(['Rango',
                       f"{f.fecha_inicio or 'inicio'} a {f.fecha_fin or 'hoy'}"])
    escritor.writerow([])

    escritor.writerow([nombre for _, nombre in def_reporte['columnas']])
    for fila in filas:
        escritor.writerow([_presentar(fila.get(clave)) for clave, _ in def_reporte['columnas']])

    # BOM UTF-8 para que Excel detecte los acentos correctamente
    contenido = '\ufeff' + salida.getvalue()
    return contenido


def _presentar(valor):
    if isinstance(valor, (datetime,)):
        return valor.strftime('%Y-%m-%d')
    if hasattr(valor, 'strftime'):
        return valor.strftime('%Y-%m-%d')
    return str(valor)


def _num(valor):
    """Convierte un Decimal/numero en float para JSON."""
    return float(valor or 0)


def reporte_json(tipo, f):
    """Filas del reporte listas para JSON (fechas y numeros serializados)."""
    filas, def_reporte = reporte(tipo, f)
    salida = []
    for fila in filas:
        objeto = {}
        for clave, _ in def_reporte['columnas']:
            valor = fila.get(clave)
            if isinstance(valor, numbers.Number):
                # Numeros (int/float/Decimal) salen como float para que el
                # frontend los formatee de forma uniforme.
                objeto[clave] = float(valor)
            else:
                objeto[clave] = _presentar(valor)
        salida.append(objeto)
    return {
        'tipo': tipo,
        'titulo': def_reporte['titulo'],
        'columnas': def_reporte['columnas'],
        'rango': {'fecha_inicio': f.fecha_inicio, 'fecha_fin': f.fecha_fin},
        'filas': salida,
    }


def exportar_html(tipo, f, empresa):
    """Genera HTML de reporte con estilos de impresion (para PDF en el
    navegador). Sin dependencias de PDF; el usuario imprime/guarda como PDF."""
    filas, def_reporte = reporte(tipo, f)

    cuerpo = "".join(
        "<tr>" + "".join(
            f"<td>{_presentar(fila.get(clave))}</td>"
            for clave, _ in def_reporte['columnas']
        ) + "</tr>"
        for fila in filas
    )

    encabezados = "".join(
        f"<th>{nombre}</th>" for _, nombre in def_reporte['columnas']
    )

    tiene_filas_tabla = encabezados and cuerpo
    total_filas = len(filas)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{def_reporte['titulo']} - InterSoft</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a1f36;
         padding: 32px; }}
  .marca {{ color: #2657d9; font-weight: 700; font-size: 20px; }}
  h1 {{ margin-top: 6px; font-size: 24px; }}
  .meta {{ color: #5a6172; font-size: 13px; margin-top: 4px; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #2657d9; color: #fff; text-align: left; padding: 8px 10px; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #e6e8ee; }}
  tr:nth-child(even) td {{ background: #f7f8fc; }}
  .pagina {{ max-width: 900px; margin: 0 auto; }}
  .pie {{ margin-top: 20px; color: #5a6172; font-size: 12px; }}
  @media print {{ body {{ padding: 0; }} }}
</style>
</head>
<body>
  <div class="pagina">
    <div class="marca">InterSoft</div>
    <h1>{def_reporte['titulo']}</h1>
    <div class="meta">
      Empresa: {_presentar(empresa.nombre)} &middot;
      Rango: {f.fecha_inicio or 'inicio'} a {f.fecha_fin or 'hoy'} &middot;
      {total_filas} registro(s) &middot;
      Generado: {timezone.localtime().strftime('%Y-%m-%d %H:%M')}
    </div>
    {f"<table><thead><tr>{encabezados}</tr></thead><tbody>{cuerpo}</tbody></table>"
     if tiene_filas_tabla else
     '<p>Sin registros para los filtros seleccionados.</p>'}
    <div class="pie">Documento generado por InterSoft &mdash; reportes de administracion.</div>
  </div>
</body>
</html>"""

