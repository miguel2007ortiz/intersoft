import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../services/auth.service';
import { authInterceptor } from './auth.interceptor';

const api = environment.apiUrl;

describe('authInterceptor', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('renueva el token y reintenta la peticion ante un 401', async () => {
    localStorage.setItem('intersoft.token', 'tok-access-viejo');
    localStorage.setItem('intersoft.refresh', 'tok-refresh-1');
    const http = TestBed.inject(HttpClient);
    const ctrl = TestBed.inject(HttpTestingController);
    const auth = TestBed.inject(AuthService);

    const promesa = firstValueFrom(http.get(`/api/clientes/`));

    const primera = ctrl.expectOne(`/api/clientes/`);
    expect(primera.request.headers.get('Authorization')).toBe('Bearer tok-access-viejo');
    primera.flush({ detalle: 'token vencido' }, { status: 401, statusText: 'Unauthorized' });

    const refresco = ctrl.expectOne(`${api}/auth/refresh/`);
    refresco.flush({ access: 'tok-access-nuevo' });

    await new Promise((resolver) => setTimeout(resolver));

    const reintento = ctrl.expectOne(`/api/clientes/`);
    expect(reintento.request.headers.get('Authorization')).toBe('Bearer tok-access-nuevo');
    reintento.flush([{ id: '1' }]);

    expect(await promesa).toEqual([{ id: '1' }]);
    expect(auth.token()).toBe('tok-access-nuevo');
  });

  it('cierra sesion y navega al login si el refresh falla', async () => {
    localStorage.setItem('intersoft.token', 'tok-access-viejo');
    localStorage.setItem('intersoft.refresh', 'tok-refresh-malo');
    const router = TestBed.inject(Router);
    const navegacion = vi.spyOn(router, 'navigate');
    const http = TestBed.inject(HttpClient);
    const ctrl = TestBed.inject(HttpTestingController);
    const auth = TestBed.inject(AuthService);

    let errorCapturado = false;
    firstValueFrom(http.get(`/api/clientes/`)).catch(() => {
      errorCapturado = true;
    });

    ctrl.expectOne(`/api/clientes/`).flush(
      { detalle: 'token vencido' },
      { status: 401, statusText: 'Unauthorized' },
    );
    ctrl.expectOne(`${api}/auth/refresh/`).error(
      new ProgressEvent('error'),
      { status: 401, statusText: 'Unauthorized' },
    );

    await new Promise((resolver) => setTimeout(resolver));

    expect(navegacion).toHaveBeenCalledWith(['/login'], { queryParams: { expirada: '1' } });
    expect(auth.token()).toBeNull();
    expect(errorCapturado).toBe(true);
  });

  it('no agrega Authorization a la peticion de refresh', () => {
    localStorage.setItem('intersoft.token', 'tok-access-viejo');
    localStorage.setItem('intersoft.refresh', 'tok-refresh-1');
    const http = TestBed.inject(HttpClient);
    const ctrl = TestBed.inject(HttpTestingController);

    http.post(`${api}/auth/refresh/`, { refresh: 'tok-refresh-1' }).subscribe();
    const peticion = ctrl.expectOne(`${api}/auth/refresh/`);
    expect(peticion.request.headers.has('Authorization')).toBe(false);
    peticion.flush({ access: 'tok-access-2' });
  });
});