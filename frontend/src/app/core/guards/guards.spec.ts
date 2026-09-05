import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';
import { provideRouter } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { adminGuard } from './admin.guard';
import { authGuard } from './auth.guard';
import { personalGuard } from './personal.guard';

function ejecutarConInyeccion(accion: () => unknown) {
  return TestBed.runInInjectionContext(accion);
}

describe('Guards de rutas', () => {
  let router: Router;
  let crearArbol: ReturnType<typeof vi.spyOn>;

  const ruta = {} as ActivatedRouteSnapshot;
  const estado = { url: '/ruta-protegida' } as RouterStateSnapshot;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([])],
    });
    router = TestBed.inject(Router);
    crearArbol = vi.spyOn(router, 'createUrlTree');
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('authGuard permite entrar con sesion activa', () => {
    vi.spyOn(TestBed.inject(AuthService), 'estaAutenticado').mockReturnValue(true);
    expect(ejecutarConInyeccion(() => authGuard(ruta, estado))).toBe(true);
    expect(crearArbol).not.toHaveBeenCalled();
  });

  it('authGuard redirige a /login con la ruta de origen cuando no hay sesion', () => {
    vi.spyOn(TestBed.inject(AuthService), 'estaAutenticado').mockReturnValue(false);
    const resultado = ejecutarConInyeccion(() => authGuard(ruta, estado));
    expect(crearArbol).toHaveBeenCalledWith(['/login'], {
      queryParams: { redirigir: '/ruta-protegida' },
    });
    expect(resultado).toBe(crearArbol.mock.results[0].value);
  });

  it('authGuard en /login redirige a esa misma ruta (sin bucle)', () => {
    vi.spyOn(TestBed.inject(AuthService), 'estaAutenticado').mockReturnValue(false);
    ejecutarConInyeccion(() =>
      authGuard({} as ActivatedRouteSnapshot, { url: '/login' } as RouterStateSnapshot));
    expect(crearArbol).toHaveBeenCalledWith(['/login'], {
      queryParams: { redirigir: '/login' },
    });
  });

  it('adminGuard deja pasar solo al ADMINISTRADOR y bloquea al resto', () => {
    const spy = vi.spyOn(TestBed.inject(AuthService), 'esAdministrador');
    spy.mockReturnValue(true);
    expect(ejecutarConInyeccion(() => adminGuard(ruta, estado))).toBe(true);

    spy.mockReturnValue(false);
    const bloqueo = ejecutarConInyeccion(() => adminGuard(ruta, estado));
    expect(crearArbol).toHaveBeenCalledWith(['/dashboard']);
    expect(bloqueo).toBe(crearArbol.mock.results[0].value);
  });

  it('personalGuard deja pasar a ADMINISTRADOR y EMPLEADO; bloquea CLIENTE', () => {
    const spy = vi.spyOn(TestBed.inject(AuthService), 'usuario');
    spy.mockReturnValue({ rol: 'ADMINISTRADOR' } as never);
    expect(ejecutarConInyeccion(() => personalGuard(ruta, estado))).toBe(true);

    spy.mockReturnValue({ rol: 'EMPLEADO' } as never);
    expect(ejecutarConInyeccion(() => personalGuard(ruta, estado))).toBe(true);

    spy.mockReturnValue({ rol: 'CLIENTE' } as never);
    ejecutarConInyeccion(() => personalGuard(ruta, estado));
    expect(crearArbol).toHaveBeenCalledWith(['/dashboard']);
  });
});