import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { CatalogoService } from './catalogo.service';
import { environment } from '../../../environments/environment';

describe('CatalogoService', () => {
  let service: CatalogoService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), CatalogoService],
    });
    service = TestBed.inject(CatalogoService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('listarClientes arma los filtros de busqueda y estado', () => {
    service.listarClientes({ busqueda: 'ana', estado: 'activo' }).subscribe();
    const req = http.expectOne((r) => r.url === `${environment.apiUrl}/clientes/`);
    expect(req.request.params.get('busqueda')).toBe('ana');
    expect(req.request.params.get('estado')).toBe('activo');
    req.flush({ resultados: [], total: 0 });
  });

  it('listarVentas envia estado y busqueda', () => {
    service.listarVentas({ estado: 'anulada', busqueda: 'FV' }).subscribe();
    const req = http.expectOne((r) => r.url === `${environment.apiUrl}/ventas/`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('estado')).toBe('anulada');
    expect(req.request.params.get('busqueda')).toBe('FV');
    req.flush({ resultados: [{}], total: 1, estadisticas: {} });
  });

  it('crearVentaPOS envia los datos al endpoint POS', () => {
    const datos = {
      cliente_id: 'c1',
      items: [{ producto: 'p1', cantidad: 2 }],
      metodo_pago: 'efectivo',
    };
    service.crearVentaPOS(datos as never).subscribe();
    const req = http.expectOne(`${environment.apiUrl}/ventas/pos/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(datos);
    req.flush({ id: 'v1' });
  });

  it('anularVenta envia motivo y POST al endpoint de anulacion', () => {
    service.anularVenta('v1', 'Error de digitacion').subscribe();
    const req = http.expectOne(`${environment.apiUrl}/ventas/v1/anular/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ motivo: 'Error de digitacion' });
    req.flush({ id: 'v1' });
  });

  it('generarFactura envia venta_id', () => {
    service.generarFactura('v1').subscribe();
    const req = http.expectOne(`${environment.apiUrl}/facturacion/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ venta_id: 'v1' });
    req.flush({ id: 'f1' });
  });

  it('ajustarInventario envia el movimiento', () => {
    const movimiento = { producto: 'p1', cantidad: 3, tipo: 'entrada', motivo: 'compra' };
    service.ajustarInventario(movimiento).subscribe();
    const req = http.expectOne(`${environment.apiUrl}/inventario/`);
    expect(req.request.body).toEqual(movimiento);
    req.flush({ id: 'm1' });
  });

  it('traduce el 403 de alertas a mensaje de personal', () => {
    service.listarAlertas().subscribe({
      error: (e) => expect(e.detalle).toBe('Solo el personal de la empresa puede hacer esto.'),
    });
    const req = http.expectOne(`${environment.apiUrl}/alertas/`);
    req.flush({ detalle: 'x' }, { status: 403, statusText: 'Forbidden' });
  });
});
