import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  DatosRol, DatosUsuario, ErrorSeguridad, PermisoCatalogo, RolAdmin, UsuarioAdmin,
} from '../models/seguridad.model';

@Injectable({ providedIn: 'root' })
export class SeguridadService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}/seguridad`;

  // ---- Usuarios ----
  listarUsuarios(): Observable<Lista<UsuarioAdmin>> {
    return this.http.get<Lista<UsuarioAdmin>>(`${this.api}/usuarios/`)
      .pipe(capturarError<Lista<UsuarioAdmin>>());
  }

  crearUsuario(datos: DatosUsuario): Observable<UsuarioAdmin> {
    return this.http.post<UsuarioAdmin>(`${this.api}/usuarios/`, datos)
      .pipe(capturarError<UsuarioAdmin>());
  }

  editarUsuario(id: string, datos: DatosUsuario): Observable<UsuarioAdmin> {
    return this.http.put<UsuarioAdmin>(`${this.api}/usuarios/${id}/`, datos)
      .pipe(capturarError<UsuarioAdmin>());
  }

  desactivarUsuario(id: string): Observable<UsuarioAdmin> {
    return this.http.post<UsuarioAdmin>(`${this.api}/usuarios/${id}/desactivar/`, {})
      .pipe(capturarError<UsuarioAdmin>());
  }

  reactivarUsuario(id: string): Observable<UsuarioAdmin> {
    return this.http.post<UsuarioAdmin>(`${this.api}/usuarios/${id}/reactivar/`, {})
      .pipe(capturarError<UsuarioAdmin>());
  }

  // ---- Roles ----
  listarRoles(): Observable<Lista<RolAdmin>> {
    return this.http.get<Lista<RolAdmin>>(`${this.api}/roles/`)
      .pipe(capturarError<Lista<RolAdmin>>());
  }

  listarPermisos(): Observable<Lista<PermisoCatalogo>> {
    return this.http.get<Lista<PermisoCatalogo>>(`${this.api}/permisos/`)
      .pipe(capturarError<Lista<PermisoCatalogo>>());
  }

  crearRol(datos: DatosRol): Observable<RolAdmin> {
    return this.http.post<RolAdmin>(`${this.api}/roles/`, datos)
      .pipe(capturarError<RolAdmin>());
  }

  editarRol(id: string, datos: Partial<DatosRol>): Observable<RolAdmin> {
    return this.http.patch<RolAdmin>(`${this.api}/roles/${id}/`, datos)
      .pipe(capturarError<RolAdmin>());
  }

  eliminarRol(id: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/roles/${id}/`)
      .pipe(capturarError<void>());
  }

  clonarRol(id: string): Observable<RolAdmin> {
    return this.http.post<RolAdmin>(`${this.api}/roles/${id}/clonar/`, {})
      .pipe(capturarError<RolAdmin>());
  }
}

/** Respuesta paginada simple del backend */
interface Lista<T> { resultados: T[]; total: number; }

/** Convierte la respuesta de error de Django en un mensaje legible. */
function capturarError<T>(): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) => throwError(() => traducir(e)));
}

function traducir(e: HttpErrorResponse): ErrorSeguridad {
  const cuerpo = (e.error ?? {}) as ErrorSeguridad;
  if (e.status === 0) return { detalle: 'No hay conexion con el servidor.' };
  if (e.status === 403) return { detalle: 'Solo el ADMINISTRADOR puede hacer esto.' };
  if (cuerpo.codigo === 'ROL_CON_USUARIOS_ACTIVOS') return cuerpo;
  if (cuerpo.errores) {
    const primerCampo = Object.values(cuerpo.errores)[0];
    const mensaje = Array.isArray(primerCampo) ? String(primerCampo[0]) : cuerpo.detalle;
    return { codigo: cuerpo.codigo, detalle: mensaje };
  }
  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
}
