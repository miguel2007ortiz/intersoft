export type RolUsuario = 'ADMINISTRADOR' | 'EMPLEADO' | 'CLIENTE';

export interface Usuario {
  id: string;
  email: string;
  nombre: string;
  rol: RolUsuario;
  empresa: string | null;
  empresa_nombre: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  usuario: Usuario;
}

export interface RegistroRequest {
  empresa: { nombre: string; nit: string };
  administrador: { nombre: string; email: string; password: string };
}

export interface RegistroCompradorRequest {
  nombre: string;
  email: string;
  password: string;
  tipo_documento: string;
  numero_documento: string;
  telefono?: string;
  direccion?: string;
  ciudad?: string;
}

export type CodigoErrorAuth =
  | 'CREDENCIALES_INVALIDAS'
  | 'CUENTA_BLOQUEADA'
  | 'USUARIO_INACTIVO'
  | 'DATOS_INVALIDOS'
  | 'SIN_CONEXION'
  | 'ERROR_SERVIDOR';

export interface ErrorAuth {
  codigo: CodigoErrorAuth;
  mensaje: string;
  intentosRestantes?: number;
  desbloqueoEn?: string;
}
