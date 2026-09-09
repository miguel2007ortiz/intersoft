import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TiendaService } from './tienda.service';
import { environment } from '../../../environments/environment';

describe('TiendaService', () => {
  let service: TiendaService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), TiendaService],
    });
    service = TestBed.inject(TiendaService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('listarCatalogo arma los parametros de filtro', () => {
    service
      .listarCatalogo({ busqueda: 'mesa', categoria: 'c1', orden: '-precio' })
      .subscribe((r) => expect(r.total).toBe(1));

    const req = http.expectOne((r) => r.url === `${environment.apiUrl}/tienda/catalogo/`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('busqueda')).toBe('mesa');
    expect(req.request.params.get('categoria')).toBe('c1');
    expect(req.request.params.get('orden')).toBe('-precio');
    req.flush({ resultados: [{}], total: 1 });
  });

  it('listarCatalogo envia la pagina y lee total_paginas', () => {
    service.listarCatalogo({ pagina: '3' }).subscribe((r) => expect(r.total_paginas).toBe(5));
    const req = http.expectOne((r) => r.url === `${environment.apiUrl}/tienda/catalogo/`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('pagina')).toBe('3');
    req.flush({ resultados: [], total: 1, total_paginas: 5 });
  });

  it('misPedidos devuelve los pedidos del comprador', () => {
    const pedido = {
      id: 'p1',
      numero_factura: 'FV-1',
      fecha: '2026-09-01',
      empresa_nombre: 'E',
      subtotal: '100',
      descuento: '0',
      total: '100',
      estado: 'completada',
      metodo_pago: 'efectivo',
      detalles: [],
      envio: null,
      created_at: '2026-09-01T00:00:00Z',
    };
    service.misPedidos().subscribe((r) => {
      expect(r.resultados[0].numero_factura).toBe('FV-1');
    });

    const req = http.expectOne(`${environment.apiUrl}/tienda/pedidos/`);
    expect(req.request.method).toBe('GET');
    req.flush({ resultados: [pedido], total: 1 });
  });

  it('checkout envia el metodo de pago', () => {
    service.checkout('tarjeta').subscribe((r) => expect(r.codigo).toBe('OK'));
    const req = http.expectOne(`${environment.apiUrl}/tienda/checkout/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ metodo_pago: 'tarjeta' });
    req.flush({ codigo: 'OK', detalle: '', ventas: [], total: '0', transaccion_id: 't1' });
  });

  it('traduce el 401 de pedidos a mensaje de sesion', () => {
    service.misPedidos().subscribe({
      error: (e) => expect(e.detalle).toBe('Debes iniciar sesion.'),
    });
    const req = http.expectOne(`${environment.apiUrl}/tienda/pedidos/`);
    req.flush({ detalle: 'x' }, { status: 401, statusText: 'Unauthorized' });
  });
});
