import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { CatalogoService } from '../../../core/services/catalogo.service';
import { AuthService } from '../../../core/services/auth.service';
import { Venta } from '../../../core/models/catalogo.model';
import { VentaDetalleComponent } from './venta-detalle.component';

const VENTA: Venta = {
  id: 'v1',
  numero_factura: 'FAC-0001',
  fecha: '2026-09-16T10:30:00Z',
  cliente: 'c1',
  cliente_nombre: 'Carlos Ramirez',
  cliente_documento: 'CC 1020304050',
  vendedor: 'u1',
  vendedor_nombre: 'Ana Ruiz',
  subtotal: '150000',
  descuento: '0',
  total: '150000',
  estado: 'completada',
  metodo_pago: 'efectivo',
  notas: '',
  motivo_anulacion: '',
  anulada_en: null,
  total_items: 2,
  detalles: [
    {
      id: 'd1',
      producto: 'p1',
      producto_nombre: 'Zapatos',
      producto_sku: 'SKU-T01',
      cantidad: 2,
      precio_unitario: '75000',
      subtotal_linea: '150000',
    },
  ],
};

describe('VentaDetalleComponent', () => {
  let catalogo: {
    obtenerVenta: ReturnType<typeof vi.fn>;
    descargarRecibo: ReturnType<typeof vi.fn>;
    reenviarRecibo: ReturnType<typeof vi.fn>;
  };

  const configurar = (id: string | null = 'v1') => {
    catalogo = {
      obtenerVenta: vi.fn(() => of(VENTA)),
      descargarRecibo: vi.fn(() => of(new Blob(['<html></html>']))),
      reenviarRecibo: vi.fn(() => of({ numero: 'RC-1', enviado_a: 'a@b.co' })),
    };
    TestBed.configureTestingModule({
      imports: [VentaDetalleComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => null,
            esAdministrador: () => false,
            tienePermiso: () => true,
          },
        },
        { provide: CatalogoService, useValue: catalogo },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => id } } },
        },
      ],
    });
  };

  const boton = (fixture: ReturnType<typeof crear>, texto: string) =>
    Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes(texto));

  const crear = () => {
    const fixture = TestBed.createComponent(VentaDetalleComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('pide la venta del id de la ruta y pinta el encabezado', () => {
    configurar('v1');
    const html = (crear().nativeElement as HTMLElement).textContent ?? '';
    expect(catalogo.obtenerVenta).toHaveBeenCalledWith('v1');
    expect(html).toContain('FAC-0001');
    expect(html).toContain('Carlos Ramirez');
    expect(html).toContain('CC 1020304050');
    expect(html).toContain('Ana Ruiz');
    expect(html).toContain('efectivo');
    expect(html).toContain('completada');
  });

  it('pinta las lineas con producto, cantidad, precio y subtotal', () => {
    configurar();
    const fixture = crear();
    const filas = (fixture.nativeElement as HTMLElement).querySelectorAll('.lineas tbody tr');
    expect(filas).toHaveLength(1);
    const texto = filas[0].textContent ?? '';
    expect(texto).toContain('Zapatos');
    expect(texto).toContain('SKU-T01');
    expect(texto).toContain('2');
    // El separador de miles depende del locale del entorno de pruebas, asi
    // que se compara sin fijarlo.
    expect(texto).toMatch(/75[.,]000/);
    expect(texto).toMatch(/150[.,]000/);
  });

  it('muestra los totales tal como vienen del API', () => {
    configurar();
    const totales =
      (crear().nativeElement as HTMLElement).querySelector('.totales')?.textContent ?? '';
    expect(totales).toContain('Subtotal');
    expect(totales).toContain('Total');
    expect(totales).toMatch(/150[.,]000/);
  });

  it('una venta de otra empresa (404) se explica sin ofrecer reintentar', () => {
    configurar();
    catalogo.obtenerVenta.mockReturnValue(throwError(() => ({ status: 404 })));
    const raiz = crear().nativeElement as HTMLElement;
    const html = raiz.textContent ?? '';
    expect(html).toContain('Venta no encontrada');
    expect(html).toContain('no pertenece a tu empresa');
    expect(html).not.toContain('Reintentar');
  });

  it('un fallo de red si ofrece reintentar', () => {
    configurar();
    catalogo.obtenerVenta
      .mockReturnValueOnce(throwError(() => ({ detalle: 'Servidor caido.' })))
      .mockReturnValue(of(VENTA));
    const fixture = crear();
    let html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('No pudimos cargar la venta');

    const boton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Reintentar'));
    boton?.click();
    fixture.detectChanges();
    html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('FAC-0001');
  });

  it('el boton Imprimir llama a window.print', () => {
    configurar();
    const imprimir = vi.spyOn(window, 'print').mockImplementation(() => undefined);
    const fixture = crear();
    const boton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Imprimir'));
    boton?.click();
    expect(imprimir).toHaveBeenCalled();
    imprimir.mockRestore();
  });

  it('una venta anulada avisa con el motivo', () => {
    configurar();
    catalogo.obtenerVenta.mockReturnValue(
      of({
        ...VENTA,
        estado: 'anulada' as const,
        motivo_anulacion: 'Error de digitacion',
        anulada_en: '2026-09-16T12:00:00Z',
      }),
    );
    const html = (crear().nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Venta anulada');
    expect(html).toContain('Error de digitacion');
  });

  it('descarga el recibo por HttpClient, no abriendo una pestana', () => {
    configurar();
    catalogo.descargarRecibo = vi.fn(() => of(new Blob(['<html></html>'])));
    const abrir = vi.spyOn(window, 'open').mockImplementation(() => null);
    const crearUrl = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:falso');
    const liberar = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);

    const fixture = crear();
    boton(fixture, 'Descargar recibo')?.click();

    expect(catalogo.descargarRecibo).toHaveBeenCalledWith('v1');
    expect(abrir).not.toHaveBeenCalled();
    expect(liberar).toHaveBeenCalledWith('blob:falso');

    abrir.mockRestore();
    crearUrl.mockRestore();
    liberar.mockRestore();
  });

  it('reenviar el recibo confirma a quien se mando', () => {
    configurar();
    catalogo.reenviarRecibo = vi.fn(() =>
      of({ numero: 'RC-FAC-0001', enviado_a: 'comprador@test.co' }),
    );
    const fixture = crear();
    boton(fixture, 'Reenviar al comprador')?.click();
    fixture.detectChanges();

    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('RC-FAC-0001');
    expect(html).toContain('comprador@test.co');
  });

  it('si el cliente no tiene correo lo explica en vez de fallar en silencio', () => {
    configurar();
    catalogo.reenviarRecibo = vi.fn(() =>
      throwError(() => ({ detalle: 'El cliente no tiene correo registrado.' })),
    );
    const fixture = crear();
    boton(fixture, 'Reenviar al comprador')?.click();
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'El cliente no tiene correo registrado.',
    );
  });
});
