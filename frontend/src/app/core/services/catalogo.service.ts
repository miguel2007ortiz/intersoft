import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Categoria, Cliente, ClienteDetalle, DatosCliente, DatosProducto, ErrorCatalogo,
  Producto, Venta, VentaPOSInput, StockInsuficiente, MovimientoInventario,
  Notificacion, InventarioProducto, FacturaElectronica, NotaCredito,
} from '../models/catalogo.model';

interface Lista<T> {
  resultados: T[];
  total: number;
  estadisticas?: Record<string, unknown>;
  pagina?: number;
  por_pagina?: number;
  total_paginas?: number;
}

@Injectable({ providedIn: 'root' })
export class CatalogoService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}`;

  // ---- Clientes ----
  listarClientes(filtros: { busqueda?: string; estado?: string; pagina?: number } = {}):
    Observable<Lista<Cliente>> {
    const params: Record<string, string> = {};
    if (filtros.busqueda) params['busqueda'] = filtros.busqueda;
    if (filtros.estado) params['estado'] = filtros.estado;
    if (filtros.pagina) params['pagina'] = String(filtros.pagina);
    return this.http.get<Lista<Cliente>>(`${this.api}/clientes/`, { params })
      .pipe(capturarError<Lista<Cliente>>());
  }

  obtenerCliente(id: string): Observable<ClienteDetalle> {
    return this.http.get<ClienteDetalle>(`${this.api}/clientes/${id}/`)
      .pipe(capturarError<ClienteDetalle>());
  }

  /** Cliente "Consumidor final" de la empresa (lo crea si no existe). Para
   * venta rapida de mostrador en el POS, sin capturar datos del comprador. */
  obtenerClienteGenerico(): Observable<Cliente> {
    return this.http.get<Cliente>(`${this.api}/clientes/generico/`)
      .pipe(capturarError<Cliente>());
  }

  crearCliente(datos: DatosCliente): Observable<Cliente> {
    return this.http.post<Cliente>(`${this.api}/clientes/`, datos)
      .pipe(capturarError<Cliente>());
  }

  editarCliente(id: string, datos: Partial<DatosCliente>): Observable<Cliente> {
    return this.http.patch<Cliente>(`${this.api}/clientes/${id}/`, datos)
      .pipe(capturarError<Cliente>());
  }

  cambiarEstadoCliente(id: string, accion: 'desactivar' | 'reactivar'): Observable<ClienteDetalle> {
    return this.http.post<ClienteDetalle>(`${this.api}/clientes/${id}/${accion}/`, {})
      .pipe(capturarError<ClienteDetalle>());
  }

  // ---- Productos ----
  listarProductos(opciones: { busqueda?: string; activo?: boolean } = {}):
    Observable<Lista<Producto>> {
      const params: Record<string, string> = {};
      if (opciones.busqueda) params['busqueda'] = opciones.busqueda;
      if (opciones.activo !== undefined) params['activo'] = String(opciones.activo);
      return this.http.get<Lista<Producto>>(`${this.api}/productos/`, { params })
        .pipe(capturarError<Lista<Producto>>());
  }

  crearProducto(datos: DatosProducto): Observable<Producto> {
    return this.http.post<Producto>(`${this.api}/productos/`, datos)
      .pipe(capturarError<Producto>());
  }

  editarProducto(id: string, datos: Partial<DatosProducto>): Observable<Producto> {
    return this.http.patch<Producto>(`${this.api}/productos/${id}/`, datos)
      .pipe(capturarError<Producto>());
  }

  cambiarEstadoProducto(id: string, accion: 'desactivar' | 'reactivar'): Observable<Producto> {
    return this.http.post<Producto>(`${this.api}/productos/${id}/${accion}/`, {})
      .pipe(capturarError<Producto>());
  }

  eliminarProducto(id: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/productos/${id}/`)
      .pipe(capturarError<void>());
  }

  // ---- Categorias ----
  listarCategorias(): Observable<Lista<Categoria>> {
    return this.http.get<Lista<Categoria>>(`${this.api}/categorias/`)
      .pipe(capturarError<Lista<Categoria>>());
  }

  crearCategoria(nombre: string): Observable<Categoria> {
    return this.http.post<Categoria>(`${this.api}/categorias/`, { nombre })
      .pipe(capturarError<Categoria>());
  }

  // ---- Ventas POS ----
  crearVentaPOS(datos: VentaPOSInput): Observable<Venta> {
    return this.http.post<Venta>(`${this.api}/ventas/pos/`, datos)
      .pipe(capturarError<Venta>());
  }

  listarVentas(filtros: { estado?: string; busqueda?: string } = {}):
    Observable<Lista<Venta>> {
    const params: Record<string, string> = {};
    if (filtros.estado) params['estado'] = filtros.estado;
    if (filtros.busqueda) params['busqueda'] = filtros.busqueda;
    return this.http.get<Lista<Venta>>(`${this.api}/ventas/`, { params })
      .pipe(capturarError<Lista<Venta>>());
  }

  obtenerVenta(id: string): Observable<Venta> {
    return this.http.get<Venta>(`${this.api}/ventas/${id}/`)
      .pipe(capturarError<Venta>());
  }

  anularVenta(id: string, motivo: string): Observable<Venta> {
    return this.http.post<Venta>(`${this.api}/ventas/${id}/anular/`, { motivo })
      .pipe(capturarError<Venta>());
  }

  // ---- Inventario ----
  listarInventario(filtros: { busqueda?: string; stock_bajo?: boolean } = {}):
    Observable<Lista<InventarioProducto>> {
    const params: Record<string, string> = {};
    if (filtros.busqueda) params['busqueda'] = filtros.busqueda;
    if (filtros.stock_bajo !== undefined) params['stock_bajo'] = String(filtros.stock_bajo);
    return this.http.get<Lista<InventarioProducto>>(`${this.api}/inventario/productos/`, { params })
      .pipe(capturarError<Lista<InventarioProducto>>());
  }

  listarMovimientos(filtros: { producto?: string; tipo?: string } = {}):
    Observable<Lista<MovimientoInventario>> {
    const params: Record<string, string> = {};
    if (filtros.producto) params['producto'] = filtros.producto;
    if (filtros.tipo) params['tipo'] = filtros.tipo;
    return this.http.get<Lista<MovimientoInventario>>(`${this.api}/inventario/`, { params })
      .pipe(capturarError<Lista<MovimientoInventario>>());
  }

  ajustarInventario(datos: { producto: string; cantidad: number; tipo: string; motivo: string }):
    Observable<MovimientoInventario> {
    return this.http.post<MovimientoInventario>(`${this.api}/inventario/`, datos)
      .pipe(capturarError<MovimientoInventario>());
  }

  // ---- Alertas ----
  listarAlertas(): Observable<Lista<Notificacion>> {
    return this.http.get<Lista<Notificacion>>(`${this.api}/alertas/`)
      .pipe(capturarError<Lista<Notificacion>>());
  }

  marcarAlertaRevisada(id: string): Observable<Notificacion> {
    return this.http.post<Notificacion>(`${this.api}/alertas/${id}/revisar/`, {})
      .pipe(capturarError<Notificacion>());
  }

  // ---- Facturacion DIAN ----
  listarFacturas(filtros: { estado?: string; busqueda?: string } = {}):
    Observable<Lista<FacturaElectronica>> {
    const params: Record<string, string> = {};
    if (filtros.estado) params['estado'] = filtros.estado;
    if (filtros.busqueda) params['busqueda'] = filtros.busqueda;
    return this.http.get<Lista<FacturaElectronica>>(`${this.api}/facturacion/`, { params })
      .pipe(capturarError<Lista<FacturaElectronica>>());
  }

  generarFactura(ventaId: string): Observable<FacturaElectronica> {
    return this.http.post<FacturaElectronica>(`${this.api}/facturacion/`, { venta_id: ventaId })
      .pipe(capturarError<FacturaElectronica>());
  }

  obtenerFactura(id: string): Observable<FacturaElectronica> {
    return this.http.get<FacturaElectronica>(`${this.api}/facturacion/${id}/`)
      .pipe(capturarError<FacturaElectronica>());
  }

  reenviarFactura(id: string, emailDestino?: string): Observable<{ detalle: string }> {
    return this.http.post<{ detalle: string }>(`${this.api}/facturacion/${id}/reenviar/`,
      emailDestino ? { email_destino: emailDestino } : {})
      .pipe(capturarError<{ detalle: string }>());
  }

  reintentarFactura(id: string): Observable<FacturaElectronica> {
    return this.http.post<FacturaElectronica>(`${this.api}/facturacion/${id}/reintentar/`, {})
      .pipe(capturarError<FacturaElectronica>());
  }

  // ---- Notas Credito ----
  listarNotasCredito(): Observable<Lista<NotaCredito>> {
    return this.http.get<Lista<NotaCredito>>(`${this.api}/notas-credito/`)
      .pipe(capturarError<Lista<NotaCredito>>());
  }

  crearNotaCredito(ventaId: string, motivo: string): Observable<NotaCredito> {
    return this.http.post<NotaCredito>(`${this.api}/notas-credito/`,
      { venta_id: ventaId, motivo })
      .pipe(capturarError<NotaCredito>());
  }

  obtenerNotaCredito(id: string): Observable<NotaCredito> {
    return this.http.get<NotaCredito>(`${this.api}/notas-credito/${id}/`)
      .pipe(capturarError<NotaCredito>());
  }
}

/** Convierte la respuesta de error de Django en un mensaje legible. */
function capturarError<T>(): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) => throwError(() => traducir(e)));
}

function traducir(e: HttpErrorResponse): ErrorCatalogo {
  const cuerpo = (e.error ?? {}) as ErrorCatalogo;
  if (e.status === 0) return { detalle: 'No hay conexion con el servidor.' };
  if (e.status === 403) {
    return { detalle: 'Solo el personal de la empresa puede hacer esto.' };
  }
  if (cuerpo.errores) {
    const primerCampo = Object.values(cuerpo.errores)[0];
    const mensaje = Array.isArray(primerCampo) ? String(primerCampo[0]) : cuerpo.detalle;
    return { codigo: cuerpo.codigo, detalle: mensaje };
  }
  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
}
