import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { CatalogoService } from '../../../core/services/catalogo.service';
import { SeguridadService } from '../../../core/services/seguridad.service';
import { AuthService } from '../../../core/services/auth.service';
import { Cliente } from '../../../core/models/catalogo.model';
import { ClientesComponent } from './clientes.component';

const CLIENTE: Cliente = {
  id: 'c1',
  nombre: 'Ana Lopez',
  tipo_documento: 'CC',
  numero_documento: '1011122233',
  email: 'ana@test.co',
  telefono: '3001234567',
  direccion: 'Cra 10 #20-30',
  ciudad: 'Bogota',
  activo: true,
  usuario_id: null,
  usuario_email: null,
  total_compras: '0',
  created_at: '2026-09-01T10:00:00Z',
};

describe('ClientesComponent', () => {
  let catalogo: {
    listarClientes: ReturnType<typeof vi.fn>;
    crearCliente: ReturnType<typeof vi.fn>;
    editarCliente: ReturnType<typeof vi.fn>;
    cambiarEstadoCliente: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    catalogo = {
      listarClientes: vi.fn(),
      crearCliente: vi.fn(),
      editarCliente: vi.fn(),
      cambiarEstadoCliente: vi.fn(),
    };
    TestBed.configureTestingModule({
      imports: [ClientesComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => null,
            esAdministrador: () => false,
            tienePermiso: () => false,
          },
        },
        {
          provide: SeguridadService,
          useValue: { listarUsuarios: vi.fn() },
        },
        { provide: CatalogoService, useValue: catalogo },
      ],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(ClientesComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('muestra error de carga con estado vacio y reintenta', () => {
    catalogo.listarClientes
      .mockReturnValueOnce(throwError(() => ({ detalle: 'Servidor caido.' })))
      .mockReturnValue(of({ resultados: [CLIENTE], total: 1, total_paginas: 1 }));
    const fixture = crear();
    let html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('No pudimos cargar los clientes');
    expect(html).toContain('Servidor caido.');
    expect(html).not.toContain('Todavia no hay clientes');

    const boton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Reintentar'));
    boton?.click();
    fixture.detectChanges();
    html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(catalogo.listarClientes).toHaveBeenCalledTimes(2);
    expect(html).toContain('Ana Lopez');
  });

  it('muestra el vacio cuando no hay clientes ni busqueda', () => {
    catalogo.listarClientes.mockReturnValue(of({ resultados: [], total: 0, total_paginas: 1 }));
    const html = crear().nativeElement.textContent ?? '';
    expect(html).toContain('Todavia no hay clientes');
  });

  it('sin resultados de busqueda ofrece limpiarla', () => {
    catalogo.listarClientes.mockReturnValue(of({ resultados: [], total: 0, total_paginas: 1 }));
    const fixture = crear();
    fixture.componentInstance.busqueda.set('zzz');
    fixture.componentInstance.cargar();
    fixture.detectChanges();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Sin resultados');
    expect(html).toContain('Limpiar busqueda');
  });
});
