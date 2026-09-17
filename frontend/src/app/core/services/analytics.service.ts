/**
 * AnalyticsService — datos del dashboard y de los reportes
 *
 * Que hace: pide al backend los indicadores ya calculados: ventas del periodo,
 * serie por dia, productos mas vendidos y comparativa con el periodo anterior.
 * Donde se usa: dashboard y /reportes.
 * Por que asi: se le pasan las fechas y agrupa el servidor. Es una consulta
 * agregada, no la lista completa de ventas: la pantalla abre igual de rapido
 * con diez ventas que con diez mil.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { capturarErrorDjango } from '../utils/django-error.util';
import {
  CategoriaFiltro,
  ClienteFrecuente,
  DatosReporte,
  FiltrosAnalitica,
  InventarioDashboard,
  ResumenDashboard,
  ResultadoLista,
  SeriesVentas,
  TipoReporte,
  TopProducto,
} from '../models/analytics.model';

/** Servicio de la fase 7: dashboard de analitica y reportes (solo ADMIN). */
@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}`;

  /** Filtros -> HttpParams conservando solo los definidos. */
  private params(filtros: FiltrosAnalitica = {}): Record<string, string> {
    const p: Record<string, string> = {};
    if (filtros.fecha_inicio) p['fecha_inicio'] = filtros.fecha_inicio;
    if (filtros.fecha_fin) p['fecha_fin'] = filtros.fecha_fin;
    if (filtros.categoria) p['categoria'] = filtros.categoria;
    return p;
  }

  resumen(f: FiltrosAnalitica = {}): Observable<ResumenDashboard> {
    return this.http
      .get<ResumenDashboard>(`${this.api}/dashboard/resumen/`, { params: this.params(f) })
      .pipe(capturarError<ResumenDashboard>());
  }

  ventas(f: FiltrosAnalitica = {}): Observable<SeriesVentas> {
    return this.http
      .get<SeriesVentas>(`${this.api}/dashboard/ventas/`, { params: this.params(f) })
      .pipe(capturarError<SeriesVentas>());
  }

  topProductos(f: FiltrosAnalitica = {}): Observable<ResultadoLista<TopProducto>> {
    return this.http
      .get<ResultadoLista<TopProducto>>(`${this.api}/dashboard/top-productos/`, {
        params: this.params(f),
      })
      .pipe(capturarError<ResultadoLista<TopProducto>>());
  }

  clientesFrecuentes(f: FiltrosAnalitica = {}): Observable<ResultadoLista<ClienteFrecuente>> {
    return this.http
      .get<ResultadoLista<ClienteFrecuente>>(`${this.api}/dashboard/clientes-frecuentes/`, {
        params: this.params(f),
      })
      .pipe(capturarError<ResultadoLista<ClienteFrecuente>>());
  }

  inventario(): Observable<InventarioDashboard> {
    return this.http
      .get<InventarioDashboard>(`${this.api}/dashboard/inventario/`)
      .pipe(capturarError<InventarioDashboard>());
  }

  categorias(): Observable<ResultadoLista<CategoriaFiltro>> {
    return this.http
      .get<ResultadoLista<CategoriaFiltro>>(`${this.api}/dashboard/categorias/`)
      .pipe(capturarError<ResultadoLista<CategoriaFiltro>>());
  }

  tiposReporte(): Observable<ResultadoLista<TipoReporte>> {
    return this.http
      .get<ResultadoLista<TipoReporte>>(`${this.api}/reportes/tipos/`)
      .pipe(capturarError<ResultadoLista<TipoReporte>>());
  }

  verReporte(tipo: string, f: FiltrosAnalitica = {}): Observable<DatosReporte> {
    const params = { tipo, ...this.params(f) };
    return this.http
      .get<DatosReporte>(`${this.api}/reportes/vista/`, { params })
      .pipe(capturarError<DatosReporte>());
  }

  /** Descarga el reporte exportado (excel=CSV con BOM, pdf=HTML de impresion).
   *
   * Va por HttpClient y NO por `window.open`: el endpoint exige JWT y el token
   * vive en localStorage, no en una cookie, asi que una pestana nueva sale sin
   * cabecera `Authorization` y el servidor responde 401. Pasando por aqui, el
   * interceptor pone el token (y renueva el access si hiciera falta).
   */
  exportarReporte(
    tipo: string,
    formato: 'excel' | 'pdf',
    f: FiltrosAnalitica = {},
  ): Observable<Blob> {
    const params = { tipo, formato, ...this.params(f) };
    return this.http
      .get(`${this.api}/reportes/exportar/`, { params, responseType: 'blob' })
      .pipe(capturarError<Blob>());
  }
}

/** Convierte la respuesta de error de Django en un mensaje legible. */
const capturarError = <T>() =>
  capturarErrorDjango<T>({
    mensajesPorStatus: { 403: 'Solo el administrador puede ver esta informacion.' },
  });
