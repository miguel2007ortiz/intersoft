/** Tipos de la fase 2: administracion de seguridad (solo ADMINISTRADOR). */

export interface UsuarioAdmin {
  id: string;
  nombre: string;
  email: string;
  rol: string;
  activo: boolean;
  es_propietario?: boolean;
  ultimo_login: string | null;
}

export interface DatosUsuario {
  nombre: string;
  email: string;
  password?: string;
  rol: string;
}

export interface PermisoCatalogo {
  codigo: string;
  descripcion: string;
}

export interface RolAdmin {
  id: string;
  nombre: string;
  descripcion: string;
  permisos: string[];
  total_usuarios_activos: number;
  es_sistema: boolean;
}

export interface DatosRol {
  nombre: string;
  descripcion: string;
  permisos: string[];
}

export interface ErrorSeguridad {
  codigo?: string;
  detalle?: string;
  errores?: Record<string, unknown>;
}
