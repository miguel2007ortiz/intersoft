import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ErrorCatalogo } from '../models/catalogo.model';
import {
  CategoriaFiltro, ClienteFrecuente, DatosReporte, FiltrosAnalitica,
  InventarioDashboard, ResumenDashboard, ResultadoLista, SeriesVentas,
  TipoReporte, TopProducto,
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
    return this.http.get<ResumenDashboard>(`${this.api}/dashboard/resumen/`, { params: this.params(f) })
      .pipe(capturarError<ResumenDashboard>());
  }

  ventas(f: FiltrosAnalitica = {}): Observable<SeriesVentas> {
    return this.http.get<SeriesVentas>(`${this.api}/dashboard/ventas/`, { params: this.params(f) })
      .pipe(capturarError<SeriesVentas>());
  }

  topProductos(f: FiltrosAnalitica = {}): Observable<ResultadoLista<TopProducto>> {
    return this.http.get<ResultadoLista<TopProducto>>(`${this.api}/dashboard/top-productos/`, { params: this.params(f) })
      .pipe(capturarError<ResultadoLista<TopProducto>>());
  }

  clientesFrecuentes(f: FiltrosAnalitica = {}): Observable<ResultadoLista<ClienteFrecuente>> {
    return this.http.get<ResultadoLista<ClienteFrecuente>>(`${this.api}/dashboard/clientes-frecuentes/`, { params: this.params(f) })
      .pipe(capturarError<ResultadoLista<ClienteFrecuente>>());
  }

  inventario(): Observable<InventarioDashboard> {
    return this.http.get<InventarioDashboard>(`${this.api}/dashboard/inventario/`)
      .pipe(capturarError<InventarioDashboard>());
  }

  categorias(): Observable<ResultadoLista<CategoriaFiltro>> {
    return this.http.get<ResultadoLista<CategoriaFiltro>>(`${this.api}/dashboard/categorias/`)
      .pipe(capturarError<ResultadoLista<CategoriaFiltro>>());
  }

  tiposReporte(): Observable<ResultadoLista<TipoReporte>> {
    return this.http.get<ResultadoLista<TipoReporte>>(`${this.api}/reportes/tipos/`)
      .pipe(capturarError<ResultadoLista<TipoReporte>>());
  }

  verReporte(tipo: string, f: FiltrosAnalitica = {}): Observable<DatosReporte> {
    const params = { tipo, ...this.params(f) };
    return this.http.get<DatosReporte>(`${this.api}/reportes/vista/`, { params })
      .pipe(capturarError<DatosReporte>());
  }

  /** Construye la URL de exportacion (excel=csv, pdf). */
  exportarUrl(tipo: string, formato: 'excel' | 'pdf', f: FiltrosAnalitica = {}): string {
    const params = new URLSearchParams(this.params(f));
    params.set('tipo', tipo);
    params.set('formato', formato);
    const query = params.toString();
    return `${this.api}/reportes/exportar/${query ? '?' + query : ''}`;
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
    return { detalle: 'Solo el administrador puede ver esta informacion.' };
  }
  if (cuerpo.errores) {
    const primerCampo = Object.values(cuerpo.errores)[0];
    const mensaje = Array.isArray(primerCampo) ? String(primerCampo[0]) : cuerpo.detalle;
    return { codigo: cuerpo.codigo, detalle: mensaje };
  }
  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
}
