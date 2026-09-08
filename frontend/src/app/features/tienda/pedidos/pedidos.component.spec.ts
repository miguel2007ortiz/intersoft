import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { PedidosComponent } from './pedidos.component';
import { TiendaService } from '../../../core/services/tienda.service';
import { Pedido } from '../../../core/models/tienda.model';

const PEDIDO_CON_ENVIO: Pedido = {
  id: 'p1',
  numero_factura: 'FV-100',
  fecha: '2026-09-01T00:00:00Z',
  empresa_nombre: 'Empresa A',
  subtotal: '100',
  descuento: '0',
  total: '100',
  estado: 'completada',
  metodo_pago: 'tarjeta',
  detalles: [],
  envio: {
    direccion: 'Cra 1 #2-3',
    ciudad: 'Bogota',
    departamento: '',
    transportadora: 'Servientrega',
    numero_guia: 'SV-9',
    estado: 'en_transito',
    estado_display: 'En transito',
    fecha_despacho: '2026-09-02T10:00:00Z',
    fecha_entrega_estimada: '2026-09-10',
    fecha_entrega_real: null,
  },
  created_at: '2026-09-01T00:00:00Z',
};

const PEDIDO_SIN_ENVIO: Pedido = { ...PEDIDO_CON_ENVIO, id: 'p2', envio: null };

describe('PedidosComponent', () => {
  let tienda: { misPedidos: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    tienda = { misPedidos: vi.fn() };
    TestBed.configureTestingModule({
      imports: [PedidosComponent],
      providers: [provideRouter([]), { provide: TiendaService, useValue: tienda }],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(PedidosComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('muestra los pedidos con su seguimiento de envio', () => {
    tienda.misPedidos.mockReturnValue(of({ resultados: [PEDIDO_CON_ENVIO], total: 1 }));
    const html = crear().nativeElement.textContent ?? '';
    expect(html).toContain('FV-100');
    expect(html).toContain('En transito');
    expect(html).toContain('Servientrega');
    expect(html).toContain('SV-9');
    expect(html).toContain('Cra 1 #2-3');
  });

  it('omite el bloque de seguimiento cuando el pedido no tiene despacho', () => {
    tienda.misPedidos.mockReturnValue(of({ resultados: [PEDIDO_SIN_ENVIO], total: 1 }));
    const fixture = crear();
    const html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('FV-100');
    expect(html).not.toContain('En transito');
    expect(fixture.nativeElement.querySelector('.envio-seguimiento')).toBeNull();
  });

  it('muestra estado vacio cuando no hay pedidos', () => {
    tienda.misPedidos.mockReturnValue(of({ resultados: [], total: 0 }));
    const html = crear().nativeElement.textContent ?? '';
    expect(html).toContain('Todavia no has hecho pedidos');
  });

  it('muestra error y reintenta la carga', () => {
    tienda.misPedidos
      .mockReturnValueOnce(throwError(() => ({ detalle: 'Servidor caido.' })))
      .mockReturnValue(of({ resultados: [PEDIDO_CON_ENVIO], total: 1 }));
    const fixture = crear();
    let html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Servidor caido.');

    const boton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Reintentar'));
    boton?.click();
    fixture.detectChanges();
    html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(tienda.misPedidos).toHaveBeenCalledTimes(2);
    expect(html).toContain('FV-100');
  });
});
