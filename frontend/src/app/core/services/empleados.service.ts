import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  DatosEmpleado, Empleado, EmpleadoCreado, EmpleadoDetalle, ErrorEmpleado, RolAsignable,
} from '../models/empleado.model';

interface Lista<T> {
  resultados: T[];
  total: number;
  pagina: number;
  por_pagina: number;
  total_paginas: number;
}

@Injectable({ providedIn: 'root' })
export class EmpleadosService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  listar(filtros: { busqueda?: string; estado?: string; pagina?: number } = {}):
    Observable<Lista<Empleado>> {
    const params: Record<string, string> = {};
    if (filtros.busqueda) params['busqueda'] = filtros.busqueda;
    if (filtros.estado) params['estado'] = filtros.estado;
    if (filtros.pagina) params['pagina'] = String(filtros.pagina);
    return this.http.get<Lista<Empleado>>(`${this.api}/empleados/`, { params })
      .pipe(capturarError<Lista<Empleado>>());
  }

  obtener(id: string): Observable<EmpleadoDetalle> {
    return this.http.get<EmpleadoDetalle>(`${this.api}/empleados/${id}/`)
      .pipe(capturarError<EmpleadoDetalle>());
  }

  crear(datos: DatosEmpleado): Observable<EmpleadoCreado> {
    return this.http.post<EmpleadoCreado>(`${this.api}/empleados/`, datos)
      .pipe(capturarError<EmpleadoCreado>());
  }

  editar(id: string, datos: Partial<DatosEmpleado>): Observable<EmpleadoDetalle> {
    return this.http.patch<EmpleadoDetalle>(`${this.api}/empleados/${id}/`, datos)
      .pipe(capturarError<EmpleadoDetalle>());
  }

  cambiarEstado(id: string, accion: 'desactivar' | 'reactivar'): Observable<EmpleadoDetalle> {
    return this.http.post<EmpleadoDetalle>(`${this.api}/empleados/${id}/${accion}/`, {})
      .pipe(capturarError<EmpleadoDetalle>());
  }

  regenerarPassword(id: string): Observable<{ password_temporal: string }> {
    return this.http.post<{ password_temporal: string }>(`${this.api}/empleados/${id}/password/`, {})
      .pipe(capturarError<{ password_temporal: string }>());
  }

  /** Roles asignables a personal (fase 2, /api/seguridad/roles/): solo lo
   * usa el selector del formulario, no se toca el resto de ese modulo. */
  listarRoles(): Observable<{ resultados: RolAsignable[] }> {
    return this.http.get<{ resultados: RolAsignable[] }>(`${this.api}/seguridad/roles/`)
      .pipe(capturarError<{ resultados: RolAsignable[] }>());
  }
}

function capturarError<T>(): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) => throwError(() => traducir(e)));
}

function traducir(e: HttpErrorResponse): ErrorEmpleado {
  const cuerpo = (e.error ?? {}) as ErrorEmpleado;
  if (e.status === 0) return { detalle: 'No hay conexion con el servidor.' };
  if (e.status === 403) return { detalle: 'No tienes permiso para hacer esto.' };
  if (cuerpo.errores) {
    const primerCampo = Object.values(cuerpo.errores)[0];
    const mensaje = Array.isArray(primerCampo) ? String(primerCampo[0]) : cuerpo.detalle;
    return { codigo: cuerpo.codigo, detalle: mensaje, empleado_inactivo_id: cuerpo.empleado_inactivo_id };
  }
  return {
    codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.',
    empleado_inactivo_id: cuerpo.empleado_inactivo_id,
  };
}
