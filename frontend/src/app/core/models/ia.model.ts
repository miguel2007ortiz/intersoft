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
