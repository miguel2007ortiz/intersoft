import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, catchError, map, of, switchMap, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CambiarPasswordRequest, ErrorAuth, LoginRequest, LoginResponse, MeResponse,
  RegistroCompradorRequest, RegistroRequest, Usuario,
} from '../models/auth.model';

const CLAVE_TOKEN = 'intersoft.token';
const CLAVE_USUARIO = 'intersoft.usuario';
const CLAVE_PERMISOS = 'intersoft.permisos';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  private readonly _token = signal<string | null>(localStorage.getItem(CLAVE_TOKEN));
  private readonly _usuario = signal<Usuario | null>(this.leerUsuarioGuardado());
  private readonly _permisos = signal<string[]>(this.leerPermisosGuardados());
  private readonly _debeCambiarPassword = signal(false);

  readonly token = this._token.asReadonly();
  readonly usuario = this._usuario.asReadonly();
  readonly permisos = this._permisos.asReadonly();
  readonly debeCambiarPassword = this._debeCambiarPassword.asReadonly();
  readonly estaAutenticado = computed(() => this._token() !== null);
  readonly esAdministrador = computed(() => this._usuario()?.rol === 'ADMINISTRADOR');

  login(datos: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.api}/auth/login/`, datos).pipe(
      tap((respuesta) => this.guardarSesion(respuesta)),
      switchMap((respuesta) => this.cargarMe().pipe(map(() => respuesta))),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirError(e))),
    );
  }

  /** Fuente unica de permisos (fase Empleados): la llama el login y, al
   * refrescar la pagina, quien arranque la app (ver app.config.ts). Si
   * falla (token vencido, etc.) no rompe nada: simplemente no hay permisos. */
  cargarMe(): Observable<MeResponse | null> {
    if (!this._token()) return of(null);
    return this.http.get<MeResponse>(`${this.api}/auth/me/`).pipe(
      tap((me) => {
        this._permisos.set(me.permisos);
        this._debeCambiarPassword.set(me.debe_cambiar_password);
        localStorage.setItem(CLAVE_PERMISOS, JSON.stringify(me.permisos));
      }),
      catchError(() => of(null)),
    );
  }

  tienePermiso(codigo: string): boolean {
    return this._permisos().includes(codigo);
  }

  cambiarPassword(datos: CambiarPasswordRequest): Observable<void> {
    return this.http.post<void>(`${this.api}/auth/cambiar-password/`, datos).pipe(
      tap(() => this._debeCambiarPassword.set(false)),
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirError(e))),
    );
  }

  cerrarSesion(): void {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_USUARIO);
    localStorage.removeItem(CLAVE_PERMISOS);
    this._token.set(null);
    this._usuario.set(null);
    this._permisos.set([]);
    this._debeCambiarPassword.set(false);
  }

  registrarEmpresa(datos: RegistroRequest): Observable<void> {
    return this.http.post<void>(`${this.api}/auth/registro/`, datos).pipe(
      catchError((e: HttpErrorResponse) => throwError(() => this.traducirError(e))),
    );
  }

  registrarComprador(datos: RegistroCompradorRequest): Observable<void> {
    return this.http.post<void>(`${this.api}/auth/registro/comprador/`, datos).pipe(
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
    localStorage.setItem(CLAVE_USUARIO, JSON.stringify(r.usuario));
    this._token.set(r.access);
    this._usuario.set(r.usuario);
    this._debeCambiarPassword.set(r.usuario.debe_cambiar_password);
  }

  private leerUsuarioGuardado(): Usuario | null {
    const crudo = localStorage.getItem(CLAVE_USUARIO);
    try {
      return crudo ? (JSON.parse(crudo) as Usuario) : null;
    } catch {
      return null;
    }
  }

  private leerPermisosGuardados(): string[] {
    const crudo = localStorage.getItem(CLAVE_PERMISOS);
    try {
      return crudo ? (JSON.parse(crudo) as string[]) : [];
    } catch {
      return [];
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
    if (e.status === 403 && cuerpo.codigo === 'EMPRESA_INACTIVA')
      return { codigo: 'EMPRESA_INACTIVA', mensaje: 'Tu empresa esta desactivada. Contacta a soporte.' };
    if (e.status === 403) return { codigo: 'USUARIO_INACTIVO', mensaje: 'Esta cuenta esta desactivada.' };
    if (e.status === 423)
      return {
        codigo: 'CUENTA_BLOQUEADA',
        mensaje: 'Cuenta bloqueada temporalmente.',
        desbloqueoEn: cuerpo.desbloqueo_en,
      };
    if (e.status === 400 && cuerpo.codigo === 'PASSWORD_ACTUAL_INCORRECTA')
      return { codigo: 'DATOS_INVALIDOS', mensaje: 'La contraseña actual no es correcta.' };
    if (e.status === 400) return { codigo: 'DATOS_INVALIDOS', mensaje: cuerpo.detalle ?? 'Datos invalidos.' };
    return { codigo: 'ERROR_SERVIDOR', mensaje: 'El servidor tuvo un problema.' };
  }
}
