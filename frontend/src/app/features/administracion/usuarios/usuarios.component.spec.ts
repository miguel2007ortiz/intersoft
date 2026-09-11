import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { ConfirmacionService } from '../../../core/services/confirmacion.service';
import { SeguridadService } from '../../../core/services/seguridad.service';
import { UsuarioAdmin } from '../../../core/models/seguridad.model';
import { UsuariosComponent } from './usuarios.component';

const ACTIVO: UsuarioAdmin = {
  id: 'u1',
  nombre: 'Ana Lopez',
  email: 'ana@empresa.co',
  rol: 'ADMINISTRADOR',
  activo: true,
  ultimo_login: null,
};

const INACTIVO: UsuarioAdmin = {
  id: 'u2',
  nombre: 'Luis Perez',
  email: 'luis@empresa.co',
  rol: 'EMPLEADO',
  activo: false,
  ultimo_login: null,
};

describe('UsuariosComponent', () => {
  let seguridad: {
    listarUsuarios: ReturnType<typeof vi.fn>;
    desactivarUsuario: ReturnType<typeof vi.fn>;
    reactivarUsuario: ReturnType<typeof vi.fn>;
  };
  let confirmacion: { pedir: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    seguridad = {
      listarUsuarios: vi.fn(),
      desactivarUsuario: vi.fn(),
      reactivarUsuario: vi.fn(),
    };
    confirmacion = { pedir: vi.fn() };
    TestBed.configureTestingModule({
      imports: [UsuariosComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => ({ email: 'yo@empresa.co' }),
            esAdministrador: () => true,
            tienePermiso: () => true,
          },
        },
        { provide: SeguridadService, useValue: seguridad },
        { provide: ConfirmacionService, useValue: confirmacion },
      ],
    });
    seguridad.listarUsuarios.mockReturnValue(
      of({ resultados: [ACTIVO, INACTIVO], total: 2, total_paginas: 1 }),
    );
  });

  const crear = () => {
    const fixture = TestBed.createComponent(UsuariosComponent);
    fixture.detectChanges();
    return fixture;
  };

  const boton = (fixture: ReturnType<typeof crear>, texto: string) =>
    Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes(texto));

  it('desactivar una cuenta activa pide confirmacion y al aceptar la desactiva', async () => {
    confirmacion.pedir.mockResolvedValue(true);
    seguridad.desactivarUsuario.mockReturnValue(of({ ...ACTIVO, activo: false }));
    const fixture = crear();

    boton(fixture, 'Desactivar')?.click();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    expect(confirmacion.pedir).toHaveBeenCalledTimes(1);
    expect(confirmacion.pedir).toHaveBeenCalledWith(
      expect.objectContaining({ titulo: 'Desactivar cuenta', destructivo: true }),
    );
    expect(seguridad.desactivarUsuario).toHaveBeenCalledWith('u1');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Cuenta desactivada.');
    expect(seguridad.reactivarUsuario).not.toHaveBeenCalled();
  });

  it('desactivar cancelado no toca el servicio y no cambia la lista', async () => {
    confirmacion.pedir.mockResolvedValue(false);
    const fixture = crear();

    boton(fixture, 'Desactivar')?.click();
    await Promise.resolve();
    fixture.detectChanges();

    expect(confirmacion.pedir).toHaveBeenCalledTimes(1);
    expect(seguridad.desactivarUsuario).not.toHaveBeenCalled();
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Cuenta desactivada.');
  });

  it('reactivar una cuenta inactiva no pide confirmacion', () => {
    seguridad.reactivarUsuario.mockReturnValue(of({ ...INACTIVO, activo: true }));
    const fixture = crear();

    boton(fixture, 'Reactivar')?.click();
    fixture.detectChanges();

    expect(confirmacion.pedir).not.toHaveBeenCalled();
    expect(seguridad.reactivarUsuario).toHaveBeenCalledWith('u2');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Cuenta reactivada.');
  });
});
