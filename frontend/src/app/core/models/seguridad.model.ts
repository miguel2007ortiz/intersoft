/**
 * Modelos de usuarios, roles y permisos (Flujo 3)
 *
 * Que hace: describe usuario, rol, permiso y los cuerpos de alta y edicion.
 * Donde se usa: SeguridadService y las pantallas de /admin.
 * Por que asi: en la edicion la contrasena es opcional (`password?`), porque
 * dejar el campo vacio significa "no la cambies" y entonces ni se envia.
 */

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
