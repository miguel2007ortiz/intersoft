/** Tipos de la fase 3: clientes y productos (personal interno). */

export interface Cliente {
  id: string;
  nombre: string;
  tipo_documento: string;
  numero_documento: string;
  email: string;
  telefono: string;
  direccion: string;
  ciudad: string;
  usuario_id: string | null;
  usuario_email: string | null;
  total_compras: string;
  created_at: string;
}

/** Datos que se envian al crear/editar: los esenciales obligatorios,
 * el resto opcional (el backend los acepta vacios). */
export type DatosCliente = Partial<Omit<Cliente, 'id' | 'usuario_email'
  | 'total_compras' | 'created_at'>> & Pick<Cliente, 'nombre' | 'tipo_documento'
  | 'numero_documento'>;

export interface Producto {
  id: string;
  nombre: string;
  descripcion: string;
  sku: string;
  categoria_id: string | null;
  categoria_nombre: string | null;
  precio: string;
  stock: number;
  stock_minimo: number;
  activo: boolean;
  stock_bajo: boolean;
  tiene_ventas: boolean;
}

export interface DatosProducto {
  nombre: string;
  descripcion: string;
  sku: string;
  categoria_id: string | null;
  precio: number;
  stock: number;
  stock_minimo: number;
}

export interface Categoria {
  id: string;
  nombre: string;
  descripcion: string;
  total_productos: number;
}

export interface ErrorCatalogo {
  codigo?: string;
  detalle?: string;
  errores?: Record<string, unknown>;
}

// ------------------------------ Fase 4: Ventas ------------------------------

export interface DetalleVenta {
  id: string;
  producto: string;
  producto_nombre: string;
  producto_sku: string;
  cantidad: number;
  precio_unitario: string;
  subtotal_linea: string;
}

export interface Venta {
  id: string;
  numero_factura: string;
  fecha: string;
  cliente: string;
  cliente_nombre: string;
  cliente_documento: string;
  vendedor: string | null;
  vendedor_nombre: string | null;
  subtotal: string;
  descuento: string;
  total: string;
  estado: 'pendiente' | 'completada' | 'anulada';
  metodo_pago: string;
  notas: string;
  motivo_anulacion: string;
  anulada_en: string | null;
  detalles: DetalleVenta[];
  total_items: number;
}

export interface LineaPOS {
  producto: string;
  nombre: string;
  sku: string;
  precio_unitario: number;
  cantidad: number;
  stock_disponible: number;
  subtotal: number;
}

export interface VentaPOSInput {
  cliente: string;
  metodo_pago: string;
  descuento: number;
  notas: string;
  detalles: { producto: string; cantidad: number }[];
}

export interface StockInsuficiente {
  producto: string;
  producto_nombre: string;
  solicitado: number;
  disponible: number;
}

export interface MovimientoInventario {
  id: string;
  producto: string;
  producto_nombre: string;
  producto_sku: string;
  usuario: string | null;
  usuario_nombre: string | null;
  tipo: 'entrada' | 'salida' | 'ajuste';
  cantidad: number;
  motivo: string;
  created_at: string;
}

export interface Notificacion {
  id: string;
  mensaje: string;
  leida: boolean;
  created_at: string;
}

export interface InventarioProducto {
  id: string;
  nombre: string;
  sku: string;
  categoria: string | null;
  precio: string;
  stock: number;
  stock_minimo: number;
  stock_bajo: boolean;
}

// ------------------------------ Fase 6: Facturacion DIAN ------------------

export interface FacturaElectronica {
  id: string;
  venta: string;
  venta_numero: string;
  cliente_nombre: string;
  cliente_documento: string;
  venta_total: string;
  numero: string;
  cufe: string;
  estado: 'pendiente' | 'enviada' | 'aprobada' | 'rechazada' | 'fallida';
  estado_display: string;
  motivo_rechazo: string;
  pdf: string | null;
  xml: string | null;
  intentos: number;
  ultimo_intento: string | null;
  enviado_correo: boolean;
  enviado_correo_en: string | null;
  created_at: string;
}

export interface NotaCredito {
  id: string;
  venta_original: string;
  venta_numero: string;
  cliente_nombre: string;
  venta_total: string;
  numero: string;
  cufe_nota: string;
  estado: 'pendiente' | 'aprobada' | 'rechazada';
  estado_display: string;
  motivo: string;
  pdf: string | null;
  xml: string | null;
  reverso_stock: boolean;
  created_at: string;
}
