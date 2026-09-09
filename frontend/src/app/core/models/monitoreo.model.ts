/** Tipos de la fase 9: monitoreo de camaras y centro de notificaciones.
 * Exclusivo del ADMINISTRADOR. */

export interface Camara {
  id: string;
  nombre: string;
  ubicacion: string;
  url_stream: string;
  activa: boolean;
  created_at: string;
  updated_at: string;
}

export interface CamaraEscritura {
  nombre: string;
  ubicacion?: string;
  url_stream?: string;
  activa?: boolean;
}

export interface GrabacionCamara {
  disponible: boolean;
  fecha?: string;
  hora?: string;
  url?: string;
  nombre?: string;
  ubicacion?: string;
  detalle?: string;
}

export interface Grabacion {
  id: string;
  camara: string;
  fecha: string;
  hora: string;
  duracion_segundos: number;
  tamano_bytes: number;
  disponible: boolean;
  url?: string;
  created_at: string;
}

export interface ResultadoGrabaciones {
  resultados: Grabacion[];
  total: number;
  pagina: number;
  por_pagina: number;
  total_paginas: number;
}

export type TipoNotificacion = 'stock' | 'factura' | 'camara' | 'sistema';
export type EstadoNotificacion = 'nueva' | 'revisada' | 'resuelta';
export type CanalNotificacion = 'ninguno' | 'whatsapp' | 'email';

export interface Notificacion {
  id: string;
  tipo: TipoNotificacion;
  tipo_display: string;
  estado: EstadoNotificacion;
  estado_display: string;
  canal: CanalNotificacion;
  canal_display: string;
  mensaje: string;
  leida: boolean;
  created_at: string;
}

export interface ResultadoListaMonitoreo<T> {
  resultados: T[];
}

export interface ErrorMonitoreo {
  codigo?: string;
  detalle?: string;
  errores?: Record<string, string[]>;
}
