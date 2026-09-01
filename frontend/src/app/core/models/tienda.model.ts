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
  created_at: string;
}
