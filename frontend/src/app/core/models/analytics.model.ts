/** Tipos de la fase 7: dashboard de analitica y reportes (solo ADMINISTRADOR). */

export interface RangoFechas {
  fecha_inicio: string | null;
  fecha_fin: string | null;
}

export interface ResumenDashboard {
  empresa_id: string;
  rango: RangoFechas;
  ingresos_totales: number;
  num_ventas: number;
  unidades_vendidas: number;
  ticket_promedio: number;
  valor_inventario: number;
  unidades_inventario: number;
  productos_bajo_minimo: number;
}

export interface VentaPorDia {
  dia: string;
  ingresos: number;
  num_ventas: number;
}

export interface VentaPorMes {
  mes: string;
  ingresos: number;
  num_ventas: number;
}

export interface SeriesVentas {
  por_dia: VentaPorDia[];
  por_mes: VentaPorMes[];
}

export interface TopProducto {
  producto: string;
  sku: string;
  categoria: string;
  unidades: number;
  ingresos: number;
}

export interface ClienteFrecuente {
  cliente: string;
  tipo_documento: string;
  numero_documento: string;
  num_ventas: number;
  total_comprado: number;
}

export interface ValorPorCategoria {
  categoria: string;
  num_productos: number;
  unidades: number;
  valor: number;
}

export interface RotacionProducto {
  producto: string;
  sku: string;
  categoria: string;
  salidas: number;
  stock_actual: number;
  rotacion: number;
}

export interface ProductoBajoMinimo {
  producto: string;
  sku: string;
  categoria: string;
  stock: number;
  stock_minimo: number;
}

export interface InventarioDashboard {
  valor_por_categoria: ValorPorCategoria[];
  rotacion: RotacionProducto[];
  bajo_minimo: ProductoBajoMinimo[];
}

export interface CategoriaFiltro {
  categoria_id: string;
  categoria: string;
}

export interface ResultadoLista<T> {
  resultados: T[];
}

export interface ColumnaReporte {
  clave: string;
  nombre: string;
}

export interface TipoReporte {
  tipo: string;
  titulo: string;
  columnas: ColumnaReporte[];
}

/** Fila generica de un reporte: valores primitivos por clave de columna. */
export type FilaReporte = Record<string, string | number>;

export interface DatosReporte {
  tipo: string;
  titulo: string;
  columnas: [string, string][];
  rango: RangoFechas;
  filas: FilaReporte[];
}

/** Filtros comunes del dashboard/reportes enviados al backend. */
export interface FiltrosAnalitica {
  fecha_inicio?: string;
  fecha_fin?: string;
  categoria?: string;
}
