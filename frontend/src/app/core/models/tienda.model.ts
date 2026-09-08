/** Tipos de la fase 5: tienda virtual, carrito y checkout. */

export interface ProductoTienda {
  id: string;
  nombre: string;
  sku: string;
  precio: string;
  stock: number;
  categoria: string | null;
  categoria_nombre: string | null;
  imagen: string | null;
  descripcion: string;
  empresa_id: string;
  empresa_nombre: string;
  created_at: string;
  promedio_calificacion: number | null;
  total_comentarios: number;
}

export interface ComentarioProducto {
  id: string;
  usuario_nombre: string;
  calificacion: number;
  comentario: string;
  created_at: string;
}

export interface DatosComentario {
  calificacion: number;
  comentario?: string;
}

export interface Favorito {
  id: string;
  producto: string;
  producto_obj: ProductoTienda;
  created_at: string;
}

export interface FavoritoEstado {
  producto: string;
  es_favorito: boolean;
}

export interface CategoriaTienda {
  id: string;
  nombre: string;
  productos_count: number;
}

export interface Cupon {
  id: string;
  codigo: string;
  porcentaje: string;
  activo: boolean;
  fecha_inicio: string;
  fecha_fin: string;
  esta_vigente: boolean;
}

export interface CarritoItem {
  id: string;
  producto: string;
  producto_nombre: string;
  producto_precio: string;
  producto_stock: number;
  cantidad: number;
  subtotal: string;
}

export interface Carrito {
  id: string;
  items: CarritoItem[];
  total_items: number;
  subtotal: string;
  descuento: string;
  total: string;
  created_at: string;
}

export interface VentaResultado {
  venta_id: string;
  numero_factura: string;
  empresa_id: string;
  empresa_nombre: string;
  total: string;
}

export interface CheckoutResponse {
  codigo: string;
  detalle: string;
  ventas: VentaResultado[];
  total: string;
  transaccion_id: string;
}

export interface StockInsuficiente {
  producto: string;
  producto_nombre: string;
  solicitado: number;
  disponible: number;
}

export interface ErrorTienda {
  codigo?: string;
  detalle?: string;
  errores?: Record<string, unknown>;
  productos?: StockInsuficiente[];
}

export interface DetallePedido {
  id: string;
  producto: string;
  producto_nombre: string;
  producto_sku: string;
  cantidad: number;
  precio_unitario: string;
  subtotal_linea: string;
}

/** Datos minimos para vincular al usuario autenticado con un Cliente del
 * marketplace cuando el checkout responde SIN_CLIENTE (RN comprador). */
export interface DatosComprador {
  tipo_documento: string;
  numero_documento: string;
  telefono?: string;
  direccion?: string;
  ciudad?: string;
}

export interface Pedido {
  id: string;
  numero_factura: string;
  fecha: string;
  empresa_nombre: string;
  subtotal: string;
  descuento: string;
  total: string;
  estado: string;
  metodo_pago: string;
  detalles: DetallePedido[];
  envio: EnvioSeguimiento | null;
  created_at: string;
}

/** Estado del despacho de una venta del marketplace (Envio.ESTADO_CHOICES
 * del backend). `entregado`/`devuelto` son terminales. */
export type EnvioEstado =
  | 'pendiente'
  | 'preparando'
  | 'despachado'
  | 'en_transito'
  | 'entregado'
  | 'no_entregado'
  | 'devuelto';

export const ENVIO_ESTADOS: { valor: EnvioEstado; etiqueta: string }[] = [
  { valor: 'pendiente', etiqueta: 'Pendiente de preparacion' },
  { valor: 'preparando', etiqueta: 'Preparando pedido' },
  { valor: 'despachado', etiqueta: 'Despachado' },
  { valor: 'en_transito', etiqueta: 'En transito' },
  { valor: 'entregado', etiqueta: 'Entregado' },
  { valor: 'no_entregado', etiqueta: 'Intento fallido' },
  { valor: 'devuelto', etiqueta: 'Devuelto al vendedor' },
];

/** Transiciones validas entre estados (Envio.TRANSICIONES_VALIDAS): desde el
 * estado actual solo se puede pasar a los listados aqui; el backend rechaza
 * cualquier otra con TRANSICION_INVALIDA. */
export const ENVIO_TRANSICIONES: Record<EnvioEstado, EnvioEstado[]> = {
  pendiente: ['preparando', 'despachado'],
  preparando: ['despachado'],
  despachado: ['en_transito', 'entregado', 'no_entregado'],
  en_transito: ['entregado', 'no_entregado'],
  no_entregado: ['en_transito', 'devuelto'],
  entregado: [],
  devuelto: [],
};

/** Seguimiento visible para el comprador (EnvioSeguimientoSerializer): solo
 * lo necesario para rastrear, sin datos internos del vendedor. */
export interface EnvioSeguimiento {
  direccion: string;
  ciudad: string;
  departamento: string;
  transportadora: string;
  numero_guia: string;
  estado: EnvioEstado;
  estado_display: string;
  fecha_despacho: string | null;
  fecha_entrega_estimada: string | null;
  fecha_entrega_real: string | null;
}

/** Envio completo para el personal interno (EnvioLecturaSerializer): el
 * seguimiento del comprador mas los datos de gestion de la empresa. */
export interface Envio extends EnvioSeguimiento {
  id: string;
  venta: string;
  numero_factura: string;
  cliente_nombre: string;
  notas: string;
  created_at: string;
  updated_at: string;
}
