import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

const api = environment.apiUrl;
const USUARIO = {
  id: '1',
  perfil_id: 'p1',
  email: 'ana@test.co',
  nombre: 'Ana',
  rol: 'ADMINISTRADOR',
  empresa: 'e1',
  empresa_nombre: 'El Progreso',
};

describe('AuthService', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    localStorage.clear();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  it('guarda la sesion con access y refresh', () => {
    const servicio = TestBed.inject(AuthService);
    servicio.login({ email: USUARIO.email, password: 'demo12345' }).subscribe();

    const peticion = http.expectOne(`${api}/auth/login/`);
    peticion.flush({ access: 'tok-access-1', refresh: 'tok-refresh-1', usuario: USUARIO });

    // El login complementa con /auth/me/ (fuente de permisos del frontend).
    http.expectOne(`${api}/auth/me/`).flush({
      ...USUARIO,
      permisos: ['empleado.leer'],
      debe_cambiar_password: false,
    });

    expect(servicio.token()).toBe('tok-access-1');
    expect(servicio.refresco()).toBe('tok-refresh-1');
    expect(servicio.estaAutenticado()).toBe(true);
    expect(localStorage.getItem('intersoft.refresh')).toBe('tok-refresh-1');
    expect(servicio.tienePermiso('empleado.leer')).toBe(true);
  });

  it('expone el id de auth_user y el del perfil por separado', () => {
    const servicio = TestBed.inject(AuthService);
    servicio.login({ email: USUARIO.email, password: 'demo12345' }).subscribe();

    http
      .expectOne(`${api}/auth/login/`)
      .flush({ access: 'tok-a', refresh: 'tok-r', usuario: USUARIO });
    http.expectOne(`${api}/auth/me/`).flush({
      ...USUARIO,
      permisos: [],
      debe_cambiar_password: false,
    });

    // `id` es el de auth_user (sujeto del token); el del Perfil va aparte.
    expect(servicio.usuario()?.id).toBe('1');
    expect(servicio.usuario()?.perfil_id).toBe('p1');
  });

  it('cargarMe refresca el usuario guardado, no solo los permisos', () => {
    const servicio = TestBed.inject(AuthService);
    servicio.login({ email: USUARIO.email, password: 'demo12345' }).subscribe();

    http
      .expectOne(`${api}/auth/login/`)
      .flush({ access: 'tok-a', refresh: 'tok-r', usuario: USUARIO });

    // Un administrador cambio el rol y la empresa despues del login: /auth/me/
    // es la fuente de verdad y tiene que pisar lo que guardo el login.
    http.expectOne(`${api}/auth/me/`).flush({
      ...USUARIO,
      rol: 'EMPLEADO',
      empresa_nombre: 'Otra Tienda',
      permisos: ['ventas.gestionar'],
      debe_cambiar_password: false,
    });

    expect(servicio.usuario()?.rol).toBe('EMPLEADO');
    expect(servicio.esAdministrador()).toBe(false);
    const guardado = JSON.parse(localStorage.getItem('intersoft.usuario') ?? '{}');
    expect(guardado.rol).toBe('EMPLEADO');
    expect(guardado.empresa_nombre).toBe('Otra Tienda');
  });

  it('devuelve false y no llama al servidor si no hay refresh token', async () => {
    localStorage.clear();
    const servicio = TestBed.inject(AuthService);

    expect(await firstValueFrom(servicio.refrescarToken())).toBe(false);
    http.expectNone(`${api}/auth/refresh/`);
  });

  it('renueva el access token con el refresh guardado', async () => {
    localStorage.setItem('intersoft.refresh', 'tok-refresh-1');
    const servicio = TestBed.inject(AuthService);

    const promesa = firstValueFrom(servicio.refrescarToken());
    const peticion = http.expectOne(`${api}/auth/refresh/`);
    expect(peticion.request.body).toEqual({ refresh: 'tok-refresh-1' });
    peticion.flush({ access: 'tok-access-2' });

    expect(await promesa).toBe(true);
    expect(servicio.token()).toBe('tok-access-2');
    expect(localStorage.getItem('intersoft.token')).toBe('tok-access-2');
  });

  it('devuelve false si el refresh falla', async () => {
    localStorage.setItem('intersoft.refresh', 'tok-refresh-malo');
    const servicio = TestBed.inject(AuthService);

    const promesa = firstValueFrom(servicio.refrescarToken());
    http
      .expectOne(`${api}/auth/refresh/`)
      .error(new ProgressEvent('error'), { status: 401, statusText: 'Unauthorized' });

    expect(await promesa).toBe(false);
  });
});
