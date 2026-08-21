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
