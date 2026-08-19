export type RolUsuario = 'ADMINISTRADOR' | 'EMPLEADO' | 'CLIENTE';

export interface Usuario {
  id: string;
  email: string;
  nombre: string;
  rol: RolUsuario;
  empresa: string;
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
