/**
 * TiendaService — toda la API del marketplace en un solo servicio
 *
 * Que hace: catalogo publico, carrito, cupones, checkout, pagos, pedidos,
 * comentarios y favoritos. Cada metodo devuelve un Observable ya tipado.
 * Donde se usa: pantallas de /catalogo, /carrito, /checkout, /pedidos y
 * /favoritos.
 * Por que asi: los errores pasan por `capturarErrorDjango`, que convierte la
 * respuesta cruda de Django en un objeto con `detalle` legible; por eso las
 * pantallas pueden hacer `e.detalle` y mostrarlo tal cual al usuario.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { capturarErrorDjango } from '../utils/django-error.util';
import {
  Carrito,
  CarritoItem,
  CategoriaTienda,
  CheckoutResultado,
  ComentarioProducto,
  Cupon,
  DatosComentario,
  DatosComprador,
  ErrorTienda,
  EstadoPago,
  Favorito,
  FavoritoEstado,
  Pedido,
  ProductoTienda,
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
  listarCatalogo(
    filtros: {
      busqueda?: string;
      categoria?: string;
      precio_min?: string;
      precio_max?: string;
      con_stock?: string;
      orden?: string;
      pagina?: string;
    } = {},
  ): Observable<Lista<ProductoTienda>> {
    const params: Record<string, string> = {};
    Object.entries(filtros).forEach(([k, v]) => {
      if (v) params[k] = v;
    });
    return this.http
      .get<Lista<ProductoTienda>>(`${this.api}/catalogo/`, { params })
      .pipe(capturarError<Lista<ProductoTienda>>());
  }

  obtenerProducto(id: string): Observable<ProductoTienda> {
    return this.http
      .get<ProductoTienda>(`${this.api}/catalogo/${id}/`)
      .pipe(capturarError<ProductoTienda>());
  }

  // ---- Comentarios / reseñas ----
  listarComentarios(productoId: string): Observable<{ resultados: ComentarioProducto[] }> {
    return this.http
      .get<{ resultados: ComentarioProducto[] }>(`${this.api}/catalogo/${productoId}/comentarios/`)
      .pipe(capturarError<{ resultados: ComentarioProducto[] }>());
  }

  /** Deja (o actualiza) el comentario propio sobre un producto. Requiere sesion. */
  comentarProducto(productoId: string, datos: DatosComentario): Observable<ComentarioProducto> {
    return this.http
      .post<ComentarioProducto>(`${this.api}/catalogo/${productoId}/comentarios/`, datos)
      .pipe(capturarError<ComentarioProducto>());
  }

  // ---- Favoritos ----
  listarFavoritos(): Observable<Favorito[]> {
    return this.http.get<Favorito[]>(`${this.api}/favoritos/`).pipe(capturarError<Favorito[]>());
  }

  /** Añade un producto a favoritos (idempotente). */
  agregarFavorito(productoId: string): Observable<Favorito> {
    return this.http
      .post<Favorito>(`${this.api}/favoritos/${productoId}/`, null)
      .pipe(capturarError<Favorito>());
  }

  /** Quita un producto de favoritos (idempotente). */
  quitarFavorito(productoId: string): Observable<void> {
    return this.http
      .delete<void>(`${this.api}/favoritos/${productoId}/`)
      .pipe(capturarError<void>());
  }

  /** Consulta si un producto es favorito del usuario autenticado. */
  consultarFavorito(productoId: string): Observable<FavoritoEstado> {
    return this.http
      .get<FavoritoEstado>(`${this.api}/favoritos/${productoId}/estado/`)
      .pipe(capturarError<FavoritoEstado>());
  }

  // ---- Cupones ----
  validarCodigo(codigo: string): Observable<Cupon> {
    return this.http
      .post<Cupon>(`${this.api}/cupones/validar/`, { codigo })
      .pipe(capturarError<Cupon>());
  }

  // ---- Carrito ----
  obtenerCarrito(): Observable<Carrito> {
    return this.http.get<Carrito>(`${this.api}/carrito/`).pipe(capturarError<Carrito>());
  }

  agregarItem(producto: string, cantidad: number): Observable<Carrito> {
    return this.http
      .post<Carrito>(`${this.api}/carrito/items/`, { producto, cantidad })
      .pipe(capturarError<Carrito>());
  }

  actualizarItem(itemId: string, cantidad: number): Observable<Carrito> {
    return this.http
      .put<Carrito>(`${this.api}/carrito/items/${itemId}/`, { cantidad })
      .pipe(capturarError<Carrito>());
  }

  eliminarItem(itemId: string): Observable<Carrito> {
    return this.http
      .delete<Carrito>(`${this.api}/carrito/items/${itemId}/`)
      .pipe(capturarError<Carrito>());
  }

  aplicarCupon(cuponId: string | null): Observable<Carrito> {
    return this.http
      .post<Carrito>(`${this.api}/carrito/cupon/`, { cupon_id: cuponId })
      .pipe(capturarError<Carrito>());
  }

  // ---- Checkout ----
  /** Con la pasarela mock devuelve la compra ya hecha (201). Con una pasarela
   * real devuelve 202 y los datos para abrir su checkout: el pago se confirma
   * despues por webhook, no en esta respuesta. */
  checkout(metodoPago: string): Observable<CheckoutResultado> {
    return this.http
      .post<CheckoutResultado>(`${this.api}/checkout/`, { metodo_pago: metodoPago })
      .pipe(capturarError<CheckoutResultado>());
  }

  /** Estado del intento de pago. Es lo que se consulta al volver de la
   * pasarela: el resultado real lo fija el webhook, no la URL de retorno. */
  estadoPago(referencia: string): Observable<EstadoPago> {
    return this.http
      .get<EstadoPago>(`${this.api}/pagos/estado/`, { params: { referencia } })
      .pipe(capturarError<EstadoPago>());
  }

  // ---- Comprador ----
  /** Vincula al usuario autenticado (admin, empleado o cliente) con un
   * Cliente del marketplace, sin exigirle una cuenta aparte. */
  completarComprador(datos: DatosComprador): Observable<void> {
    return this.http
      .post<void>(`${this.api}/completar-comprador/`, datos)
      .pipe(capturarError<void>());
  }

  // ---- Pedidos del comprador ----
  misPedidos(): Observable<{ resultados: Pedido[]; total: number }> {
    return this.http
      .get<{ resultados: Pedido[]; total: number }>(`${this.api}/pedidos/`)
      .pipe(capturarError<{ resultados: Pedido[]; total: number }>());
  }
}

const capturarError = <T>() =>
  capturarErrorDjango<T>({
    mensajesPorStatus: { 401: 'Debes iniciar sesion.' },
  });
