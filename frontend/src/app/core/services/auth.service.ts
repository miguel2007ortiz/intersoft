import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import {
  Observable, catchError, finalize, firstValueFrom, from, map, of, tap, throwError,
} from 'rxjs';
import { environment } from '../../../environments/environment';
import { ErrorAuth, LoginRequest, LoginResponse, RegistroRequest, Usuario } from '../models/auth.model';

const CLAVE_TOKEN = 'intersoft.token';
const CLAVE_REFRESH = 'intersoft.refresh';
const CLAVE_USUARIO = 'intersoft.usuario';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  private readonly _token = signal<string | null>(localStorage.getItem(CLAVE_TOKEN));
  private readonly _refresco = signal<string | null>(localStorage.getItem(CLAVE_REFRESH));
  private readonly _usuario = signal<Usuario | null>(this.leerUsuarioGuardado());
  private refrescoEnProgreso: Promise<boolean> | null = null;

  readonly token = this._token.asReadonly();
  readonly refresco = this._refresco.asReadonly();
  readonly usuario = this._usuario.asReadonly();
  readonly estaAutenticado = computed(() => this._token() !== null);
  readonly esAdministrador = computed(() => this._usuario()?.rol === 'ADMINISTRADOR');

  login(datos: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.api}/auth/login/`, datos).pipe(
      tap((respuesta) => this.guardarSesion(respuesta)),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirError(e))),
    );
  }

  cerrarSesion(): void {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_REFRESH);
    localStorage.removeItem(CLAVE_USUARIO);
    this._token.set(null);
    this._refresco.set(null);
    this._usuario.set(null);
  }

  refrescarToken(): Observable<boolean> {
    const refresco = this._refresco();
    if (!refresco) return of(false);
    if (this.refrescoEnProgreso) return from(this.refrescoEnProgreso);

    this.refrescoEnProgreso = firstValueFrom(
      this.http
        .post<{ access: string }>(`${this.api}/auth/refresh/`, { refresh: refresco })
        .pipe(
          tap((r) => {
            localStorage.setItem(CLAVE_TOKEN, r.access);
            this._token.set(r.access);
          }),
          map(() => true),
          catchError(() => of(false)),
          finalize(() => {
            this.refrescoEnProgreso = null;
          }),
        ),
    );
    return from(this.refrescoEnProgreso);
  }

  registrarEmpresa(datos: RegistroRequest): Observable<void> {
    return this.http.post<void>(`${this.api}/auth/registro/`, datos).pipe(
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirError(e))),
    );
  }

  emailDisponible(email: string): Observable<boolean> {
    return this.http
      .get<{ disponible: boolean }>(`${this.api}/auth/email-disponible/`, { params: { email } })
      .pipe(map((r) => r.disponible));
  }

  solicitarRecuperacion(email: string): Observable<void> {
    return this.http.post<void>(`${this.api}/auth/password-reset/`, { email }).pipe(
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirError(e))),
    );
  }

  restablecerPassword(token: string, password: string): Observable<void> {
    return this.http.post<void>(`${this.api}/auth/password-reset/confirmar/`, { token, password }).pipe(
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirError(e))),
    );
  }

  private guardarSesion(r: LoginResponse): void {
    localStorage.setItem(CLAVE_TOKEN, r.access);
    localStorage.setItem(CLAVE_REFRESH, r.refresh);
    localStorage.setItem(CLAVE_USUARIO, JSON.stringify(r.usuario));
    this._token.set(r.access);
    this._refresco.set(r.refresh);
    this._usuario.set(r.usuario);
  }

  private leerUsuarioGuardado(): Usuario | null {
    const crudo = localStorage.getItem(CLAVE_USUARIO);
    try {
      return crudo ? (JSON.parse(crudo) as Usuario) : null;
    } catch {
      return null;
    }
  }

  private traducirError(e: HttpErrorResponse): ErrorAuth {
    const cuerpo = e.error ?? {};
    if (e.status === 0) return { codigo: 'SIN_CONEXION', mensaje: 'No hay conexion con el servidor.' };
    if (e.status === 401)
      return {
        codigo: 'CREDENCIALES_INVALIDAS',
        mensaje: 'Correo o contraseña incorrectos.',
        intentosRestantes: cuerpo.intentos_restantes,
      };
    if (e.status === 403) return { codigo: 'USUARIO_INACTIVO', mensaje: 'Esta cuenta esta desactivada.' };
    if (e.status === 423)
      return {
        codigo: 'CUENTA_BLOQUEADA',
        mensaje: 'Cuenta bloqueada temporalmente.',
        desbloqueoEn: cuerpo.desbloqueo_en,
      };
    if (e.status === 400) return { codigo: 'DATOS_INVALIDOS', mensaje: cuerpo.detalle ?? 'Datos invalidos.' };
    return { codigo: 'ERROR_SERVIDOR', mensaje: 'El servidor tuvo un problema.' };
  }
}
