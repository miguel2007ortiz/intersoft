import { TestBed } from '@angular/core/testing';
import { EstadoVacioComponent } from './estado-vacio.component';

describe('EstadoVacioComponent', () => {
  it('renderiza el contenedor por defecto con role status', () => {
    const fixture = TestBed.createComponent(EstadoVacioComponent);
    fixture.detectChanges();
    const estado = (fixture.nativeElement as HTMLElement).querySelector('.estado');
    expect(estado).not.toBeNull();
    expect(estado?.getAttribute('aria-live')).toBe('polite');
  });

  it('muestra titulo y mensaje cuando se proveen', () => {
    const fixture = TestBed.createComponent(EstadoVacioComponent);
    fixture.componentRef.setInput('titulo', 'Sin resultados');
    fixture.componentRef.setInput('mensaje', 'No se encontro nada con ese filtro.');
    fixture.detectChanges();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Sin resultados');
    expect(html).toContain('No se encontro nada con ese filtro.');
  });

  it('emite la accion al pulsar el boton', () => {
    const fixture = TestBed.createComponent(EstadoVacioComponent);
    const accion = vi.fn();
    fixture.componentInstance.accion.subscribe(accion);
    fixture.componentRef.setInput('accionTexto', 'Reintentar');
    fixture.detectChanges();

    const boton = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('button');
    expect(boton).not.toBeNull();
    boton?.click();
    expect(accion).toHaveBeenCalledTimes(1);
  });

  it('marca el tipo error con aria-live assertive', () => {
    const fixture = TestBed.createComponent(EstadoVacioComponent);
    fixture.componentRef.setInput('tipo', 'error');
    fixture.detectChanges();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('[aria-live="assertive"]'),
    ).not.toBeNull();
  });
});
