import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { EnviosService } from '../../core/services/envios.service';
import { AuthService } from '../../core/services/auth.service';
import { Envio } from '../../core/models/tienda.model';
import { EnviosComponent } from './envios.component';

const ENVIO: Envio = {
  id: 'e1',
  venta: 'v1',
  numero_factura: 'FV-1001',
  cliente_nombre: 'Cliente Uno',
  direccion: 'Cra 10 #20-30',
  ciudad: 'Bogota',
  departamento: '',
  transportadora: '',
  numero_guia: '',
  estado: 'pendiente',
  estado_display: 'Pendiente de preparacion',
  fecha_despacho: null,
  fecha_entrega_estimada: null,
  fecha_entrega_real: null,
  notas: '',
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-01T10:00:00Z',
};

describe('EnviosComponent', () => {
  let servicio: {
    listarEnvios: ReturnType<typeof vi.fn>;
    obtenerEnvio: ReturnType<typeof vi.fn>;
    actualizarEnvio: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    servicio = {
      listarEnvios: vi.fn(),
      obtenerEnvio: vi.fn(),
      actualizarEnvio: vi.fn(),
    };
    TestBed.configureTestingModule({
      imports: [EnviosComponent],
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
        { provide: EnviosService, useValue: servicio },
      ],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(EnviosComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('carga los envios al iniciar y los muestra', () => {
    servicio.listarEnvios.mockReturnValue(of({ resultados: [ENVIO], total: 1 }));
    const fixture = crear();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(servicio.listarEnvios).toHaveBeenCalledWith(undefined);
    expect(html).toContain('FV-1001');
    expect(html).toContain('Pendiente de preparacion');
    expect(html).toContain('Cliente Uno');
  });

  it('filtra por estado y re-consulta la API', () => {
    servicio.listarEnvios.mockReturnValue(of({ resultados: [], total: 0 }));
    const fixture = crear();
    fixture.componentInstance.filtroEstado = 'despachado';
    fixture.componentInstance.cargarEnvios();
    fixture.detectChanges();
    expect(servicio.listarEnvios).toHaveBeenLastCalledWith('despachado');
  });

  it('muestra estado vacio cuando no hay envios', () => {
    servicio.listarEnvios.mockReturnValue(of({ resultados: [], total: 0 }));
    const html = crear().nativeElement.textContent ?? '';
    expect(html).toContain('No hay envios');
  });

  it('muestra error con reintento cuando falla la carga', () => {
    servicio.listarEnvios
      .mockReturnValueOnce(throwError(() => ({ detalle: 'Servidor caido.' })))
      .mockReturnValue(of({ resultados: [ENVIO], total: 1 }));
    const fixture = crear();
    let html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Servidor caido.');
    expect(html).toContain('Reintentar');

    const boton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Reintentar'));
    boton?.click();
    fixture.detectChanges();
    html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(servicio.listarEnvios).toHaveBeenCalledTimes(2);
    expect(html).toContain('FV-1001');
  });

  it('abre el modal de gestion con las transiciones validas', () => {
    servicio.listarEnvios.mockReturnValue(of({ resultados: [ENVIO], total: 1 }));
    const fixture = crear();
    fixture.componentInstance.gestionar(ENVIO);
    fixture.detectChanges();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Gestionar envio');
    expect(html).toContain('Preparando pedido');
    expect(html).toContain('Despachado');
  });

  it('guarda los cambios y recarga la lista', () => {
    servicio.listarEnvios.mockReturnValue(of({ resultados: [ENVIO], total: 1 }));
    servicio.actualizarEnvio.mockReturnValue(of({ ...ENVIO, estado: 'preparando' }));
    const fixture = crear();
    fixture.componentInstance.gestionar(ENVIO);
    fixture.componentInstance.transportadora = 'Servientrega';
    fixture.componentInstance.numeroGuia = 'SV-1';
    fixture.componentInstance.notas = 'piso 3';
    fixture.componentInstance.elegirEstado('preparando');
    fixture.componentInstance.guardar();
    fixture.detectChanges();

    expect(servicio.actualizarEnvio).toHaveBeenCalledWith('v1', {
      transportadora: 'Servientrega',
      numero_guia: 'SV-1',
      notas: 'piso 3',
      fecha_entrega_estimada: null,
      estado: 'preparando',
    });
    expect(servicio.listarEnvios).toHaveBeenCalledTimes(2);
  });

  it('muestra el error del guardado dentro del modal', () => {
    servicio.listarEnvios.mockReturnValue(of({ resultados: [ENVIO], total: 1 }));
    servicio.actualizarEnvio.mockReturnValue(
      throwError(() => ({ detalle: 'Transicion invalida.' })),
    );
    const fixture = crear();
    fixture.componentInstance.gestionar(ENVIO);
    fixture.componentInstance.elegirEstado('entregado');
    fixture.componentInstance.guardar();
    fixture.detectChanges();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Transicion invalida.');
  });
});
