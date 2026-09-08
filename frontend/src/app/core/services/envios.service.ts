import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { capturarErrorDjango } from '../utils/django-error.util';
import { Envio, EnvioEstado } from '../models/tienda.model';

export interface DatosActualizarEnvio {
  estado?: EnvioEstado;
  transportadora?: string;
  numero_guia?: string;
  fecha_entrega_estimada?: string | null;
  notas?: string;
}

interface ListaEnvios {
  resultados: Envio[];
  total: number;
}

/** API de despachos para el personal interno (EsPersonal): /api/envios/ y
 * /api/ventas/<id>/envio/. El comprador sigue viendo el seguimiento dentro
 * de su Pedido (TiendaService.misPedidos), sin endpoint aparte. */
@Injectable({ providedIn: 'root' })
export class EnviosService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}`;

  listarEnvios(estado?: EnvioEstado): Observable<ListaEnvios> {
    const params: Record<string, string> = {};
    if (estado) params['estado'] = estado;
    return this.http
      .get<ListaEnvios>(`${this.api}/envios/`, { params })
      .pipe(capturarError<ListaEnvios>());
  }

  obtenerEnvio(ventaId: string): Observable<Envio> {
    return this.http
      .get<Envio>(`${this.api}/ventas/${ventaId}/envio/`)
      .pipe(capturarError<Envio>());
  }

  actualizarEnvio(ventaId: string, datos: DatosActualizarEnvio): Observable<Envio> {
    return this.http
      .patch<Envio>(`${this.api}/ventas/${ventaId}/envio/`, datos)
      .pipe(capturarError<Envio>());
  }
}

/** Convierte la respuesta de error de Django en un mensaje legible. */
const capturarError = <T>() =>
  capturarErrorDjango<T>({
    mensajesPorStatus: { 403: 'Solo el personal de la empresa puede gestionar envios.' },
  });
