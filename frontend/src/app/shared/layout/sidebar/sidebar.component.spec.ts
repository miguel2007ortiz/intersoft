import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { SidebarComponent } from './sidebar.component';

function crearMql(esEscritorio: boolean) {
  const evento = (matches: boolean) => ({ matches, media: '(min-width: 1024px)' }) as MediaQueryListEvent;
  const listeners = new Set<(e: MediaQueryListEvent) => void>();
  const mql = {
    matches: esEscritorio,
    media: '(min-width: 1024px)',
    addEventListener: vi.fn((_tipo: string, cb: (e: MediaQueryListEvent) => void) => {
      listeners.add(cb);
    }),
    removeEventListener: vi.fn((_tipo: string, cb: (e: MediaQueryListEvent) => void) => {
      listeners.delete(cb);
    }),
    dispatch: (matches: boolean) => listeners.forEach((cb) => cb(evento(matches))),
  };
  return mql;
}

describe('SidebarComponent', () => {
  const mql = crearMql(true);

  beforeEach(() => {
    vi.stubGlobal('matchMedia', vi.fn(() => mql));
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [SidebarComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: { usuario: () => null, esAdministrador: () => false, tienePermiso: () => false } },
      ],
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('arranca en escritorio y cambia con el media query', () => {
    const fixture = TestBed.createComponent(SidebarComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance.esEscritorio()).toBe(true);

    mql.dispatch(false);
    expect(fixture.componentInstance.esEscritorio()).toBe(false);

    mql.dispatch(true);
    expect(fixture.componentInstance.esEscritorio()).toBe(true);
  });

  it('alterna el colapso y lo recuerda en localStorage', () => {
    const fixture = TestBed.createComponent(SidebarComponent);
    fixture.detectChanges();
    const instancia = fixture.componentInstance;

    expect(instancia.colapsado()).toBe(false);
    instancia.alternarColapso();
    expect(instancia.colapsado()).toBe(true);
    expect(localStorage.getItem('intersoft.sidebar-colapsado')).toBe('1');

    instancia.alternarColapso();
    expect(instancia.colapsado()).toBe(false);
    expect(localStorage.getItem('intersoft.sidebar-colapsado')).toBe('0');
  });

  it('libera el listener del media query al destruirse', () => {
    const fixture = TestBed.createComponent(SidebarComponent);
    fixture.detectChanges();
    const listenersAntes = mql.removeEventListener.mock.calls.length;

    fixture.destroy();
    expect(mql.removeEventListener).toHaveBeenCalledTimes(listenersAntes + 1);
  });
});