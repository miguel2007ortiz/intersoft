import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { capturarErrorDjango } from '../utils/django-error.util';
import {
  Camara, CamaraEscritura, GrabacionCamara,
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

/** Convierte la respuesta de error de Django en un mensaje legible. */
const capturarErrorMonitoreo = <T,>() =>
  capturarErrorDjango<T>({
    mensajesPorStatus: { 403: 'Solo el administrador puede ver esta informacion.' },
  });
