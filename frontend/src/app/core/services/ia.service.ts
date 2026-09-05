import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { capturarErrorDjango, ErrorDjango } from '../utils/django-error.util';
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

/** Convierte la respuesta de error de Django en un mensaje legible,
 * conservando la conversacion cuando el motor de IA falla (502). */
const capturarErrorIA = <T,>() =>
  capturarErrorDjango<T, ErrorIA>({
    enriquecer: (e, cuerpo, base) => {
      const conConversacion = e.status === 502 && !!cuerpo['conversacion'];
      if (!conConversacion) return base as ErrorIA & ErrorDjango;
      return {
        ...base,
        codigo: typeof cuerpo['codigo'] === 'string' ? cuerpo['codigo'] : 'IA_NO_DISPONIBLE',
        detalle:
          typeof cuerpo['detalle'] === 'string'
            ? cuerpo['detalle']
            : 'El asistente no pudo responder en este momento.',
        conversacion: cuerpo['conversacion'] as ConversacionIA,
      } as ErrorIA & ErrorDjango;
    },
  });
