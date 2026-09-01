import { TestBed } from '@angular/core/testing';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { NavProgressComponent } from './nav-progress.component';

describe('NavProgressComponent', () => {
  let eventos: Subject<object>;

  beforeEach(() => {
    eventos = new Subject();
    TestBed.configureTestingModule({
      imports: [NavProgressComponent],
      providers: [{ provide: Router, useValue: { events: eventos } as unknown as Router }],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('muestra la barra durante la navegacion y la oculta al terminar', () => {
    vi.useFakeTimers();
    const fixture = TestBed.createComponent(NavProgressComponent);
    fixture.detectChanges();
    const instancia = fixture.componentInstance;

    eventos.next(new NavigationStart(1, '/ventas'));
    expect(instancia.visible()).toBe(true);
    expect(instancia.completa()).toBe(false);

    eventos.next(new NavigationEnd(1, '/ventas', '/ventas'));
    expect(instancia.completa()).toBe(true);
    vi.advanceTimersByTime(259);
    expect(instancia.visible()).toBe(true);
    vi.advanceTimersByTime(1);
    expect(instancia.visible()).toBe(false);
  });

  it('deja de reaccionar a eventos del router al destruirse (sin fugas)', () => {
    const fixture = TestBed.createComponent(NavProgressComponent);
    fixture.detectChanges();
    const instancia = fixture.componentInstance;

    fixture.destroy();
    eventos.next(new NavigationStart(2, '/clientes'));
    expect(instancia.visible()).toBe(false);
    expect(instancia.completa()).toBe(false);
  });
});