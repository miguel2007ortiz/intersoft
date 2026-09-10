import { TestBed } from '@angular/core/testing';
import { ConfirmacionComponent } from './confirmacion.component';
import { ConfirmacionService } from '../../core/services/confirmacion.service';

describe('ConfirmacionComponent', () => {
  let servicio: ConfirmacionService;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [ConfirmacionComponent] });
    servicio = TestBed.inject(ConfirmacionService);
  });

  function montar() {
    const fixture = TestBed.createComponent(ConfirmacionComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('no dibuja nada mientras no haya confirmacion pendiente', () => {
    const fixture = montar();
    expect(fixture.nativeElement.querySelector('.dialogo')).toBeNull();
  });

  it('muestra titulo y mensaje, y resuelve a true al confirmar', async () => {
    const fixture = montar();
    const respuesta = servicio.pedir({ titulo: 'Eliminar rol', mensaje: 'Se ira para siempre.' });
    fixture.detectChanges();

    const dialogo = fixture.nativeElement.querySelector('.dialogo') as HTMLElement;
    expect(dialogo.getAttribute('role')).toBe('alertdialog');
    expect(dialogo.textContent).toContain('Eliminar rol');
    expect(dialogo.textContent).toContain('Se ira para siempre.');

    fixture.componentInstance.confirmar();
    await expect(respuesta).resolves.toBe(true);
  });

  it('resuelve a false al cancelar y cierra el dialogo', async () => {
    const fixture = montar();
    const respuesta = servicio.pedir({ titulo: 'Confirmar', mensaje: 'Seguro?' });
    fixture.detectChanges();

    fixture.componentInstance.cancelar();
    fixture.detectChanges();

    await expect(respuesta).resolves.toBe(false);
    expect(fixture.nativeElement.querySelector('.dialogo')).toBeNull();
  });

  it('Escape cancela la confirmacion', async () => {
    const fixture = montar();
    const respuesta = servicio.pedir({ titulo: 'Confirmar', mensaje: 'Seguro?' });
    fixture.detectChanges();

    fixture.componentInstance.cancelarConEscape();
    await expect(respuesta).resolves.toBe(false);
  });

  it('en una accion destructiva avisa que no se puede deshacer', () => {
    const fixture = montar();
    servicio.pedir({ titulo: 'Eliminar', mensaje: 'Adios.', destructivo: true });
    fixture.detectChanges();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('no se puede deshacer');
    expect(fixture.nativeElement.querySelector('.btn-destructivo')).not.toBeNull();
  });

  it('abrir una segunda confirmacion cancela la anterior, sin apilarlas', async () => {
    const fixture = montar();
    const primera = servicio.pedir({ titulo: 'Uno', mensaje: 'Primero' });
    const segunda = servicio.pedir({ titulo: 'Dos', mensaje: 'Segundo' });
    fixture.detectChanges();

    await expect(primera).resolves.toBe(false);
    expect(fixture.nativeElement.querySelectorAll('.dialogo').length).toBe(1);

    fixture.componentInstance.confirmar();
    await expect(segunda).resolves.toBe(true);
  });
});
