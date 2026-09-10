import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { MonitoreoService } from '../../core/services/monitoreo.service';
import { AuthService } from '../../core/services/auth.service';
import { Camara, CamaraEscritura, Grabacion } from '../../core/models/monitoreo.model';
import { CamarasComponent } from './camaras.component';

const CAMARA: Camara = {
  id: 'c1',
  nombre: 'Entrada principal',
  ubicacion: 'Recepcion',
  url_stream: 'https://cam.example/live/1',
  activa: true,
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-01T10:00:00Z',
};

const GRABACION: Grabacion = {
  id: 'g1',
  camara: 'c1',
  fecha: '2026-09-01',
  hora: '12:00:00',
  duracion_segundos: 75,
  tamano_bytes: 2 * 1024 * 1024,
  disponible: true,
  url: '/media/streams/e/c1/2026-09-01/12_00.mp4',
  created_at: '2026-09-01T12:05:00Z',
};

describe('CamarasComponent', () => {
  let servicio: {
    camaras: ReturnType<typeof vi.fn>;
    crearCamara: ReturnType<typeof vi.fn>;
    editarCamara: ReturnType<typeof vi.fn>;
    eliminarCamara: ReturnType<typeof vi.fn>;
    grabacion: ReturnType<typeof vi.fn>;
    grabacionesCamera: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    servicio = {
      camaras: vi.fn(),
      crearCamara: vi.fn(),
      editarCamara: vi.fn(),
      eliminarCamara: vi.fn(),
      grabacion: vi.fn(),
      grabacionesCamera: vi.fn(),
    };
    TestBed.configureTestingModule({
      imports: [CamarasComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => null,
            esAdministrador: () => true,
            tienePermiso: () => false,
          },
        },
        { provide: MonitoreoService, useValue: servicio },
      ],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(CamarasComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('carga las camaras al iniciar', () => {
    servicio.camaras.mockReturnValue(of({ resultados: [CAMARA] }));
    const fixture = crear();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(servicio.camaras).toHaveBeenCalled();
    expect(html).toContain('Entrada principal');
    expect(html).toContain('Recepcion');
  });

  it('crea una camara y recarga el listado', () => {
    servicio.camaras.mockReturnValue(of({ resultados: [] }));
    servicio.crearCamara.mockReturnValue(of(CAMARA));
    const fixture = crear();
    const comp = fixture.componentInstance;
    comp.nombre.set('Bodega');
    comp.ubicacion.set('Deposito');
    comp.urlStream.set('rtsp://cam.example/3');
    comp.crearCamara();
    fixture.detectChanges();
    const datos: CamaraEscritura = {
      nombre: 'Bodega',
      ubicacion: 'Deposito',
      url_stream: 'rtsp://cam.example/3',
    };
    expect(servicio.crearCamara).toHaveBeenCalledWith(datos);
    expect(servicio.camaras).toHaveBeenCalledTimes(2);
    expect(comp.mostrandoForm()).toBe(false);
  });

  it('muestra el error si no se puede cargar el listado', () => {
    servicio.camaras.mockReturnValue(
      throwError(() => ({ codigo: 'ERROR', detalle: 'Algo fallo' })),
    );
    const fixture = crear();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Algo fallo');
  });

  it('al seleccionar una camara carga el catalogo de grabaciones', () => {
    servicio.camaras.mockReturnValue(of({ resultados: [CAMARA] }));
    servicio.grabacionesCamera.mockReturnValue(
      of({ resultados: [GRABACION], total: 1, pagina: 1, por_pagina: 50, total_paginas: 1 }),
    );
    const fixture = crear();
    fixture.componentInstance.seleccionar(CAMARA);
    fixture.detectChanges();
    expect(servicio.grabacionesCamera).toHaveBeenCalledWith('c1', { pagina: 1 });
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('2026-09-01');
    expect(html).toContain('12:00');
    expect(html).toContain('2.0 MB');
  });

  it('marca como no disponible la grabacion sin archivo en disco', () => {
    servicio.camaras.mockReturnValue(of({ resultados: [CAMARA] }));
    servicio.grabacionesCamera.mockReturnValue(
      of({
        resultados: [{ ...GRABACION, disponible: false, url: undefined }],
        total: 1,
        pagina: 1,
        por_pagina: 50,
        total_paginas: 1,
      }),
    );
    const fixture = crear();
    fixture.componentInstance.seleccionar(CAMARA);
    fixture.detectChanges();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Sin archivo');
  });

  it('reproducir consulta la grabacion por fecha/hora de la sesion', () => {
    servicio.camaras.mockReturnValue(of({ resultados: [CAMARA] }));
    servicio.grabacionesCamera.mockReturnValue(
      of({ resultados: [GRABACION], total: 1, pagina: 1, por_pagina: 50, total_paginas: 1 }),
    );
    servicio.grabacion.mockReturnValue(
      of({ disponible: true, fecha: '2026-09-01', hora: '12:00:00', url: GRABACION.url }),
    );
    const fixture = crear();
    const comp = fixture.componentInstance;
    comp.seleccionar(CAMARA);
    fixture.detectChanges();
    comp.reproducir(GRABACION);
    fixture.detectChanges();
    expect(servicio.grabacion).toHaveBeenCalledWith('c1', '2026-09-01', '12:00');
  });

  it('cambia de pagina en el catalogo', () => {
    servicio.camaras.mockReturnValue(of({ resultados: [CAMARA] }));
    servicio.grabacionesCamera.mockReturnValue(of([])).mockReset();
    servicio.grabacionesCamera
      .mockReturnValueOnce(
        of({ resultados: [GRABACION], total: 51, pagina: 1, por_pagina: 50, total_paginas: 2 }),
      )
      .mockReturnValueOnce(
        of({ resultados: [], total: 51, pagina: 2, por_pagina: 50, total_paginas: 2 }),
      );
    const fixture = crear();
    const comp = fixture.componentInstance;
    comp.seleccionar(CAMARA);
    fixture.detectChanges();
    comp.irPagina(2);
    fixture.detectChanges();
    expect(servicio.grabacionesCamera).toHaveBeenLastCalledWith('c1', { pagina: 2 });
    expect(comp.paginaGrabaciones()).toBe(2);
  });

  it('formatea tamanos y duraciones legibles', () => {
    const comp = TestBed.createComponent(CamarasComponent).componentInstance;
    expect(comp.tamanoLegible(2 * 1024 * 1024)).toBe('2.0 MB');
    expect(comp.tamanoLegible(500)).toBe('500 B');
    expect(comp.duracionLegible(75)).toBe('1 min 15 s');
    expect(comp.duracionLegible(0)).toBe('Duracion no registrada');
  });
});
