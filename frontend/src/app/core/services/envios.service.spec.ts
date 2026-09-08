import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { EnviosService } from './envios.service';
import { environment } from '../../../environments/environment';

describe('EnviosService', () => {
  let service: EnviosService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), EnviosService],
    });
    service = TestBed.inject(EnviosService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('listarEnvios sin filtro consulta la cola completa', () => {
    service.listarEnvios().subscribe();
    const req = http.expectOne(`${environment.apiUrl}/envios/`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.keys().length).toBe(0);
    req.flush({ resultados: [{}], total: 1 });
  });

  it('listarEnvios agrega el parametro de estado', () => {
    service.listarEnvios('despachado').subscribe();
    const req = http.expectOne((r) => r.url === `${environment.apiUrl}/envios/`);
    expect(req.request.params.get('estado')).toBe('despachado');
    req.flush({ resultados: [], total: 0 });
  });

  it('obtenerEnvio llama al detalle de la venta', () => {
    service.obtenerEnvio('v1').subscribe((e) => expect(e.numero_factura).toBe('FV-1'));
    const req = http.expectOne(`${environment.apiUrl}/ventas/v1/envio/`);
    expect(req.request.method).toBe('GET');
    req.flush({ id: 'e1', numero_factura: 'FV-1' });
  });

  it('actualizarEnvio hace PATCH con los campos modificados', () => {
    service
      .actualizarEnvio('v1', {
        estado: 'preparando',
        transportadora: 'Servientrega',
        notas: 'piso 3',
      })
      .subscribe();
    const req = http.expectOne(`${environment.apiUrl}/ventas/v1/envio/`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({
      estado: 'preparando',
      transportadora: 'Servientrega',
      notas: 'piso 3',
    });
    req.flush({ id: 'e1' });
  });

  it('traduce el 403 a mensaje de personal', () => {
    service.listarEnvios().subscribe({
      error: (e) =>
        expect(e.detalle).toBe('Solo el personal de la empresa puede gestionar envios.'),
    });
    const req = http.expectOne(`${environment.apiUrl}/envios/`);
    req.flush({ detalle: 'x' }, { status: 403, statusText: 'Forbidden' });
  });
});
