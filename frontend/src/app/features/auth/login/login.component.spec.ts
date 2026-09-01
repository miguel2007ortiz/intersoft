import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { LoginComponent } from './login.component';
import { provideHttpClient } from '@angular/common/http';

@Component({
  selector: 'app-prueba',
  template: '',
})
class PruebaComponent {}

describe('LoginComponent (redireccion segura)', () => {
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideRouter([
          { path: 'login', component: LoginComponent },
          { path: 'dashboard', component: PruebaComponent },
          { path: 'tienda', component: PruebaComponent },
        ]),
        provideHttpClient(),
      ],
    });
    localStorage.clear();
    router = TestBed.inject(Router);
  });

  const destinoActual = (): string => {
    const fixture = TestBed.createComponent(LoginComponent);
    const destino = (fixture.componentInstance as unknown as { destinoDespuesDeLogin(): string })
      .destinoDespuesDeLogin();
    fixture.destroy();
    return destino;
  };

  it('redirige a una ruta interna valida tras el login', async () => {
    await router.navigate(['/login'], { queryParams: { redirigir: '/tienda' } });
    expect(destinoActual()).toBe('/tienda');
  });

  it('ignora redirigir invalido (rutas externas //) y usa /dashboard', async () => {
    await router.navigate(['/login'], { queryParams: { redirigir: '//evil.example' } });
    expect(destinoActual()).toBe('/dashboard');
  });

  it('sin redirigir usa /dashboard', () => {
    expect(destinoActual()).toBe('/dashboard');
  });
});