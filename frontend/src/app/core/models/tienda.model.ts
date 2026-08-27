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

export interface CheckoutResponse {
  codigo: string;
  detalle: string;
  venta_id: string;
  numero_factura: string;
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
