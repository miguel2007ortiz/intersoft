import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ConversacionIA, ConversacionIAResumen, ErrorIA, RespuestaChatIA,
  ResultadoListaIA,
} from '../models/ia.model';

/** Servicio del asistente IA (fase 8): conversaciones y chat.
 * Disponible para ADMINISTRADOR y EMPLEADO. */
@Injectable({ providedIn: 'root' })
export class IaService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}`;

  conversaciones(): Observable<ResultadoListaIA<ConversacionIAResumen>> {
    return this.http.get<ResultadoListaIA<ConversacionIAResumen>>(
      `${this.api}/ia/conversaciones/`).pipe(capturarErrorIA());
  }

  crearConversacion(titulo?: string): Observable<ConversacionIA> {
    return this.http.post<ConversacionIA>(
      `${this.api}/ia/conversaciones/`, { titulo }).pipe(capturarErrorIA());
  }

  detalle(id: string): Observable<ConversacionIA> {
    return this.http.get<ConversacionIA>(
      `${this.api}/ia/conversaciones/${id}/`).pipe(capturarErrorIA());
  }

  enviar(mensaje: string, conversacionId?: string): Observable<RespuestaChatIA> {
    const cuerpo: Record<string, string> = { mensaje };
    if (conversacionId) cuerpo['conversacion_id'] = conversacionId;
    return this.http.post<RespuestaChatIA>(
      `${this.api}/ia/chat/`, cuerpo).pipe(capturarErrorIA());
  }
}

function capturarErrorIA<T>(): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) => throwError(() => traducirIA(e)));
}

function traducirIA(e: HttpErrorResponse): ErrorIA {
  const cuerpo = (e.error ?? {}) as ErrorIA;
  if (e.status === 0) {
    return { codigo: 'SIN_CONEXION', detalle: 'No hay conexion con el servidor.' };
  }
  if (e.status === 502 && cuerpo.conversacion) {
    // El motor fallo pero la conversacion se conservo para reintentar.
    return {
      codigo: cuerpo.codigo ?? 'IA_NO_DISPONIBLE',
      detalle: cuerpo.detalle ?? 'El asistente no pudo responder en este momento.',
      conversacion: cuerpo.conversacion,
    };
  }
  if (cuerpo.errores) {
    const primerCampo = Object.values(cuerpo.errores)[0];
    const mensaje = Array.isArray(primerCampo) ? String(primerCampo[0]) : cuerpo.detalle;
    return { codigo: cuerpo.codigo, detalle: mensaje };
  }
  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
}
