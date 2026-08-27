import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Camara, CamaraEscritura, ErrorMonitoreo, GrabacionCamara,
  Notificacion, ResultadoListaMonitoreo,
} from '../models/monitoreo.model';

/** Servicio de la fase 9: monitoreo de camaras y notificaciones.
 * Exclusivo del ADMINISTRADOR. */
@Injectable({ providedIn: 'root' })
export class MonitoreoService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}`;

  camaras(activas?: boolean): Observable<ResultadoListaMonitoreo<Camara>> {
    const params: Record<string, string> = {};
    if (activas !== undefined) params['activas'] = activas ? '1' : '0';
    return this.http.get<ResultadoListaMonitoreo<Camara>>(
      `${this.api}/camaras/`, { params }).pipe(capturarErrorMonitoreo());
  }

  crearCamara(datos: CamaraEscritura): Observable<Camara> {
    return this.http.post<Camara>(`${this.api}/camaras/`, datos)
      .pipe(capturarErrorMonitoreo());
  }

  detalleCamara(id: string): Observable<Camara> {
    return this.http.get<Camara>(`${this.api}/camaras/${id}/`)
      .pipe(capturarErrorMonitoreo());
  }

  editarCamara(id: string, datos: Partial<CamaraEscritura>): Observable<Camara> {
    return this.http.patch<Camara>(`${this.api}/camaras/${id}/`, datos)
      .pipe(capturarErrorMonitoreo());
  }

  eliminarCamara(id: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/camaras/${id}/`)
      .pipe(capturarErrorMonitoreo());
  }

  grabacion(id: string, fecha: string, hora: string): Observable<GrabacionCamara> {
    return this.http.get<GrabacionCamara>(
      `${this.api}/camaras/${id}/grabacion/`, { params: { fecha, hora } })
      .pipe(capturarErrorMonitoreo());
  }

  notificaciones(incluirResueltas = false): Observable<ResultadoListaMonitoreo<Notificacion>> {
    return this.http.get<ResultadoListaMonitoreo<Notificacion>>(
      `${this.api}/notificaciones/`,
      { params: incluirResueltas ? { incluir_resueltas: '1' } : {} })
      .pipe(capturarErrorMonitoreo());
  }

  marcarNotificacion(id: string, estado: 'revisada' | 'resuelta'): Observable<Notificacion> {
    return this.http.patch<Notificacion>(
      `${this.api}/notificaciones/${id}/`, { estado })
      .pipe(capturarErrorMonitoreo());
  }
}

function capturarErrorMonitoreo<T>(): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) => throwError(() => traducir(e)));
}

function traducir(e: HttpErrorResponse): ErrorMonitoreo {
  const cuerpo = (e.error ?? {}) as ErrorMonitoreo;
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
