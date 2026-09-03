/** Tipos del modulo Empleados (personal interno), separado de Clientes. */

import { VentaResumen } from './catalogo.model';

export interface Empleado {
  id: string;
  nombre: string;
  email: string;
  rol: string;
  tipo_documento: string | null;
  numero_documento: string | null;
  telefono: string;
  cargo: string;
  fecha_ingreso: string | null;
  es_propietario: boolean;
  activo: boolean;
  ultimo_login: string | null;
}

export interface EmpleadoDetalle extends Empleado {
  ultimas_ventas: VentaResumen[];
}

/** Respuesta de creacion: igual al detalle, mas la contrasena temporal
 * (RN-09) cuando el servidor la genero por no venir en la peticion. */
export interface EmpleadoCreado extends EmpleadoDetalle {
  password_temporal?: string;
}

export interface DatosEmpleado {
  nombre: string;
  email: string;
  password?: string;
  rol: string;
  tipo_documento?: string | null;
  numero_documento?: string | null;
  telefono?: string;
  cargo?: string;
  fecha_ingreso?: string | null;
}

/** Rol asignable a personal, tal como lo devuelve /api/seguridad/roles/
 * (fase 2 admin), reusado aqui solo para poblar el selector del formulario. */
export interface RolAsignable {
  id: string;
  nombre: string;
}

export interface ErrorEmpleado {
  codigo?: string;
  detalle?: string;
  errores?: Record<string, unknown>;
  empleado_inactivo_id?: string;
}
