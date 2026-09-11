import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { AnalyticsService } from '../../core/services/analytics.service';
import { DashboardComponent } from './dashboard.component';

describe('DashboardComponent', () => {
  let analytics: {
    categorias: ReturnType<typeof vi.fn>;
    resumen: ReturnType<typeof vi.fn>;
    ventas: ReturnType<typeof vi.fn>;
    topProductos: ReturnType<typeof vi.fn>;
    clientesFrecuentes: ReturnType<typeof vi.fn>;
    inventario: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    analytics = {
      categorias: vi.fn(() => of({ resultados: [] })),
      resumen: vi.fn(() => of({})),
      ventas: vi.fn(() => of({ por_dia: [], por_mes: [] })),
      topProductos: vi.fn(() => of({ resultados: [], total: 0, total_paginas: 1 })),
      clientesFrecuentes: vi.fn(() => of({ resultados: [], total: 0, total_paginas: 1 })),
      inventario: vi.fn(() => of({ valor_por_categoria: [] })),
    };
    TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => ({
              nombre: 'Admin Demo',
              empresa_nombre: 'El Progreso',
              email: 'a@b.co',
            }),
            esAdministrador: () => true,
            tienePermiso: () => true,
          },
        },
        { provide: AnalyticsService, useValue: analytics },
      ],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('rango invertido deshabilita Aplicar y muestra aviso, sin pedir datos', () => {
    const fixture = crear();
    const llamadas = analytics.resumen.mock.calls.length;
    expect(llamadas).toBe(1);
    fixture.componentInstance.fechaInicio.set('2026-10-01');
    fixture.componentInstance.fechaFin.set('2026-09-01');
    fixture.detectChanges();

    const html = fixture.nativeElement as HTMLElement;
    expect(html.textContent).toContain('El rango de fechas es invalido');
    const aplicar = Array.from(html.querySelectorAll<HTMLButtonElement>('button')).find((b) =>
      b.textContent?.includes('Aplicar'),
    );
    expect(aplicar?.disabled).toBe(true);

    aplicar?.click();
    expect(analytics.resumen.mock.calls.length).toBe(llamadas);
  });

  it('rango valido no bloquea Aplicar', () => {
    const fixture = crear();
    fixture.componentInstance.fechaInicio.set('2026-09-01');
    fixture.componentInstance.fechaFin.set('2026-09-30');
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain(
      'El rango de fechas es invalido',
    );
  });
});
