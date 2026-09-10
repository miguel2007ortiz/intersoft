/**
 * Modelos del asistente de IA — contrato de datos con /api/ia/
 *
 * Que hace: describe en TypeScript lo que el backend manda y recibe en el chat
 * del asistente y en las sugerencias.
 * Donde se usa: IaService y la pantalla /ia.
 * Por que asi: los campos conservan el nombre exacto de la API (snake_case).
 * No se renombran a camelCase para no mantener una capa de traduccion que solo
 * anade sitios donde equivocarse.
 */

export interface ResultadoListaIA<T> {
  resultados: T[];
}

export type RolMensajeIA = 'usuario' | 'asistente';
export type EstadoMensajeIA = 'ok' | 'error';
export type EstadoConversacionIA = 'activa' | 'archivada';

export interface MensajeIA {
  id: string;
  rol: RolMensajeIA;
  contenido: string;
  estado: EstadoMensajeIA;
  error: string;
  created_at: string;
}

export interface ConversacionIA {
  id: string;
  titulo: string;
  estado: EstadoConversacionIA;
  ultimo_mensaje: string;
  mensajes: MensajeIA[];
  created_at: string;
  updated_at: string;
}

export interface ConversacionIAResumen {
  id: string;
  titulo: string;
  estado: EstadoConversacionIA;
  ultimo_mensaje: string;
  created_at: string;
}

export interface RespuestaChatIA {
  respuesta: string;
  contexto: string;
  conversacion: ConversacionIA;
}

export interface ErrorIA {
  codigo: string;
  detalle: string;
  conversacion?: ConversacionIA;
  errores?: Record<string, string[]>;
}
