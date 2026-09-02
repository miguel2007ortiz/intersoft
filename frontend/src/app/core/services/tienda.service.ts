import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { capturarErrorDjango } from '../utils/django-error.util';
import {
  Carrito, CarritoItem, CategoriaTienda, CheckoutResponse,
  ComentarioProducto, Cupon, DatosComentario, DatosComprador,
  ErrorTienda, Pedido, ProductoTienda,
} from '../models/tienda.model';

interface Lista<T> {
  resultados: T[];
  total: number;
  categorias?: CategoriaTienda[];
  pagina?: number;
  por_pagina?: number;
  total_paginas?: number;
}

@Injectable({ providedIn: 'root' })
export class TiendaService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}/tienda`;

  // ---- Catálogo público ----
  listarCatalogo(filtros: { busqueda?: string; categoria?: string; precio_min?: string; precio_max?: string; con_stock?: string; orden?: string; pagina?: string } = {}):
    Observable<Lista<ProductoTienda>> {
    const params: Record<string, string> = {};
    Object.entries(filtros).forEach(([k, v]) => { if (v) params[k] = v; });
    return this.http.get<Lista<ProductoTienda>>(`${this.api}/catalogo/`, { params })
      .pipe(capturarError<Lista<ProductoTienda>>());
  }

  obtenerProducto(id: string): Observable<ProductoTienda> {
    return this.http.get<ProductoTienda>(`${this.api}/catalogo/${id}/`)
      .pipe(capturarError<ProductoTienda>());
  }

  // ---- Comentarios / reseñas ----
  listarComentarios(productoId: string): Observable<{ resultados: ComentarioProducto[] }> {
    return this.http.get<{ resultados: ComentarioProducto[] }>(
      `${this.api}/catalogo/${productoId}/comentarios/`)
      .pipe(capturarError<{ resultados: ComentarioProducto[] }>());
  }

  /** Deja (o actualiza) el comentario propio sobre un producto. Requiere sesion. */
  comentarProducto(productoId: string, datos: DatosComentario): Observable<ComentarioProducto> {
    return this.http.post<ComentarioProducto>(
      `${this.api}/catalogo/${productoId}/comentarios/`, datos)
      .pipe(capturarError<ComentarioProducto>());
  }

  // ---- Cupones ----
  validarCodigo(codigo: string): Observable<Cupon> {
    return this.http.post<Cupon>(`${this.api}/cupones/validar/`, { codigo })
      .pipe(capturarError<Cupon>());
  }

  // ---- Carrito ----
  obtenerCarrito(): Observable<Carrito> {
    return this.http.get<Carrito>(`${this.api}/carrito/`)
      .pipe(capturarError<Carrito>());
  }

  agregarItem(producto: string, cantidad: number): Observable<Carrito> {
    return this.http.post<Carrito>(`${this.api}/carrito/items/`, { producto, cantidad })
      .pipe(capturarError<Carrito>());
  }

  actualizarItem(itemId: string, cantidad: number): Observable<Carrito> {
    return this.http.put<Carrito>(`${this.api}/carrito/items/${itemId}/`, { producto: itemId, cantidad })
      .pipe(capturarError<Carrito>());
  }

  eliminarItem(itemId: string): Observable<Carrito> {
    return this.http.delete<Carrito>(`${this.api}/carrito/items/${itemId}/`)
      .pipe(capturarError<Carrito>());
  }

  aplicarCupon(cuponId: string | null): Observable<Carrito> {
    return this.http.post<Carrito>(`${this.api}/carrito/cupon/`, { cupon_id: cuponId })
      .pipe(capturarError<Carrito>());
  }

  // ---- Checkout ----
  checkout(metodoPago: string): Observable<CheckoutResponse> {
    return this.http.post<CheckoutResponse>(`${this.api}/checkout/`, { metodo_pago: metodoPago })
      .pipe(capturarError<CheckoutResponse>());
  }

  // ---- Comprador ----
  /** Vincula al usuario autenticado (admin, empleado o cliente) con un
   * Cliente del marketplace, sin exigirle una cuenta aparte. */
  completarComprador(datos: DatosComprador): Observable<void> {
    return this.http.post<void>(`${this.api}/completar-comprador/`, datos)
      .pipe(capturarError<void>());
  }

  // ---- Pedidos del comprador ----
  misPedidos(): Observable<{ resultados: Pedido[]; total: number }> {
    return this.http.get<{ resultados: Pedido[]; total: number }>(`${this.api}/pedidos/`)
      .pipe(capturarError<{ resultados: Pedido[]; total: number }>());
  }
}

const capturarError = <T,>() =>
  capturarErrorDjango<T>({
    mensajesPorStatus: { 401: 'Debes iniciar sesion.' },
  });
