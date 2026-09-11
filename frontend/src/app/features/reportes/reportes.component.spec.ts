import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { AnalyticsService } from '../../core/services/analytics.service';
import { ReportesComponent } from './reportes.component';

describe('ReportesComponent', () => {
  let analytics: {
    tiposReporte: ReturnType<typeof vi.fn>;
    categorias: ReturnType<typeof vi.fn>;
    verReporte: ReturnType<typeof vi.fn>;
    exportarUrl: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    analytics = {
      tiposReporte: vi.fn(() => of({ resultados: [{ tipo: 'ventas', titulo: 'Ventas por dia' }] })),
      categorias: vi.fn(() => of({ resultados: [] })),
      verReporte: vi.fn(() =>
        of({ titulo: 'Ventas por dia', columnas: [], filas: [], total: 0, total_paginas: 1 }),
      ),
      exportarUrl: vi.fn(() => 'http://api.test/exportar'),
    };
    TestBed.configureTestingModule({
      imports: [ReportesComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => null,
            esAdministrador: () => true,
            tienePermiso: () => true,
          },
        },
        { provide: AnalyticsService, useValue: analytics },
      ],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(ReportesComponent);
    fixture.detectChanges();
    return fixture;
  };

  const boton = (fixture: ReturnType<typeof crear>, texto: string) =>
    Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes(texto));

  it('rango invertido deshabilita Generar y exportar, y muestra aviso', () => {
    const fixture = crear();
    fixture.componentInstance.fechaInicio.set('2026-10-01');
    fixture.componentInstance.fechaFin.set('2026-09-01');
    fixture.detectChanges();

    const html = fixture.nativeElement as HTMLElement;
    expect(html.textContent).toContain('El rango de fechas es invalido');
    expect(boton(fixture, 'Generar')?.disabled).toBe(true);
    expect(boton(fixture, 'Excel')?.disabled).toBe(true);
    expect(boton(fixture, 'PDF')?.disabled).toBe(true);
    expect(analytics.verReporte).not.toHaveBeenCalled();
  });

  it('rango valido permite generar y exportar', () => {
    const fixture = crear();
    fixture.componentInstance.fechaInicio.set('2026-09-01');
    fixture.componentInstance.fechaFin.set('2026-09-30');
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain(
      'El rango de fechas es invalido',
    );
    expect(boton(fixture, 'Generar')?.disabled).toBe(false);

    boton(fixture, 'Generar')?.click();
    expect(analytics.verReporte).toHaveBeenCalledWith(
      'ventas',
      expect.objectContaining({ fecha_inicio: '2026-09-01', fecha_fin: '2026-09-30' }),
    );
  });
});
