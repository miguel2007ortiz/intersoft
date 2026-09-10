import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import { ConfirmacionService } from '../../../core/services/confirmacion.service';
import { CatalogoComponent } from './catalogo.component';

const api = environment.apiUrl;

/** Responde a las llamadas de arranque para dejar el componente listo. */
function despacharArranque(ctrl: HttpTestingController): void {
  ctrl
    .match((r) => r.url.startsWith(api))
    .forEach((r) =>
      r.flush(r.request.url.includes('/favoritos') ? [] : { resultados: [], count: 0, items: [] }),
    );
}

describe('CatalogoComponent - favoritos', () => {
  beforeEach(() => {
    localStorage.clear();
    // jsdom no trae IntersectionObserver, que usa la directiva de revelado.
    (globalThis as unknown as { IntersectionObserver: unknown }).IntersectionObserver = class {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    };
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
  });

  afterEach(() => localStorage.clear());

  it('sin sesion no llama a la API y ofrece iniciar sesion con el dialogo propio', () => {
    const fixture = TestBed.createComponent(CatalogoComponent);
    fixture.detectChanges();
    const ctrl = TestBed.inject(HttpTestingController);
    despacharArranque(ctrl);

    fixture.componentInstance.alternarFavorito({ id: 'p1', nombre: 'Cafe' } as never);

    ctrl.expectNone(`${api}/tienda/favoritos/p1/`);
    expect(TestBed.inject(ConfirmacionService).abierta()).not.toBeNull();
  });

  it('con sesion guarda el favorito y pinta el corazon', () => {
    localStorage.setItem('intersoft.token', 'tok');
    const fixture = TestBed.createComponent(CatalogoComponent);
    fixture.detectChanges();
    const ctrl = TestBed.inject(HttpTestingController);
    expect(TestBed.inject(AuthService).estaAutenticado()).toBe(true);
    despacharArranque(ctrl);

    fixture.componentInstance.alternarFavorito({ id: 'p1', nombre: 'Cafe' } as never);
    ctrl.expectOne({ method: 'POST', url: `${api}/tienda/favoritos/p1/` }).flush({ id: 'f1' });

    expect(fixture.componentInstance.esFavorito('p1')).toBe(true);
  });

  it('si la API falla avisa en vez de fallar en silencio', () => {
    localStorage.setItem('intersoft.token', 'tok');
    const fixture = TestBed.createComponent(CatalogoComponent);
    fixture.detectChanges();
    const ctrl = TestBed.inject(HttpTestingController);
    despacharArranque(ctrl);

    fixture.componentInstance.alternarFavorito({ id: 'p1', nombre: 'Cafe' } as never);
    ctrl
      .expectOne({ method: 'POST', url: `${api}/tienda/favoritos/p1/` })
      .flush({ detalle: 'Producto no encontrado.' }, { status: 404, statusText: 'Not Found' });

    expect(fixture.componentInstance.avisoError()).toBe('Producto no encontrado.');
    expect(fixture.componentInstance.esFavorito('p1')).toBe(false);
  });
});
