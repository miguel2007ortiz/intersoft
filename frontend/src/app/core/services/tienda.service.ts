import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Carrito, CarritoItem, CategoriaTienda, CheckoutResponse,
  Cupon, DatosComprador, ErrorTienda, Pedido, ProductoTienda,
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

function capturarError<T>(): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) => throwError(() => traducir(e)));
}

function traducir(e: HttpErrorResponse): ErrorTienda {
  const cuerpo = (e.error ?? {}) as ErrorTienda;
  if (e.status === 0) return { detalle: 'No hay conexion con el servidor.' };
  if (e.status === 401) return { detalle: 'Debes iniciar sesion.' };
  if (cuerpo.errores) {
    const primerCampo = Object.values(cuerpo.errores)[0];
    const mensaje = Array.isArray(primerCampo) ? String(primerCampo[0]) : cuerpo.detalle;
    return { codigo: cuerpo.codigo, detalle: mensaje };
  }
  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
}
