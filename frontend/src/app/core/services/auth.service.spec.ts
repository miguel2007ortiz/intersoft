import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

const api = environment.apiUrl;
const USUARIO = {
  id: 'u1',
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

    expect(servicio.token()).toBe('tok-access-1');
    expect(servicio.refresco()).toBe('tok-refresh-1');
    expect(servicio.estaAutenticado()).toBe(true);
    expect(localStorage.getItem('intersoft.refresh')).toBe('tok-refresh-1');
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
    http.expectOne(`${api}/auth/refresh/`).error(
      new ProgressEvent('error'),
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(await promesa).toBe(false);
  });
});