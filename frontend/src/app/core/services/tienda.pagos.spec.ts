import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../environments/environment';
import {
  CheckoutPendiente,
  CheckoutResponse,
  CheckoutResultado,
  EstadoPago,
  esCheckoutPendiente,
} from '../models/tienda.model';
import { TiendaService } from './tienda.service';

const api = `${environment.apiUrl}/tienda`;

const PENDIENTE: CheckoutPendiente = {
  codigo: 'PAGO_PENDIENTE',
  detalle: 'Redirige al comprador al checkout de Wompi.',
  referencia: 'ref-abc123',
  total: '50000.00',
  pasarela: 'wompi',
  datos_checkout: {
    url: 'https://checkout.wompi.co/p/',
    public_key: 'pub_test_llave',
    currency: 'COP',
    amount_in_cents: 5000000,
    reference: 'ref-abc123',
    signature_integrity: 'firma',
    redirect_url: 'http://localhost:4200/pago/retorno',
  },
};

const RESUELTO: CheckoutResponse = {
  codigo: 'EXITO',
  detalle: 'Compra realizada exitosamente.',
  ventas: [],
  total: '50000.00',
  transaccion_id: 'MOCK-1',
};

describe('TiendaService - pagos (Fase 4)', () => {
  let http: HttpTestingController;
  let servicio: TiendaService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    servicio = TestBed.inject(TiendaService);
  });

  afterEach(() => http.verify());

  it('trata el 202 del checkout como respuesta valida, no como error', () => {
    // Un 202 es 2xx: si se manejara como error, el comprador nunca llegaria a
    // la pasarela y el checkout parecerian roto pese a haber reservado stock.
    let recibido: CheckoutResultado | null = null;
    servicio.checkout('tarjeta').subscribe((r) => (recibido = r));

    http.expectOne(`${api}/checkout/`).flush(PENDIENTE, {
      status: 202,
      statusText: 'Accepted',
    });

    expect(recibido).not.toBeNull();
    expect(esCheckoutPendiente(recibido!)).toBe(true);
  });

  it('distingue un checkout resuelto de uno pendiente', () => {
    let recibido: CheckoutResultado | null = null;
    servicio.checkout('tarjeta').subscribe((r) => (recibido = r));
    http.expectOne(`${api}/checkout/`).flush(RESUELTO, { status: 201, statusText: 'Created' });

    expect(esCheckoutPendiente(recibido!)).toBe(false);
  });

  it('consulta el estado del pago por referencia', () => {
    const estado: EstadoPago = {
      codigo: 'OK',
      referencia: 'ref-abc123',
      estado: 'aprobado',
      pasarela: 'wompi',
      transaccion_id: 'wompi-tx-1',
      total: '50000.00',
      ventas: [],
    };
    let recibido: EstadoPago | null = null;
    servicio.estadoPago('ref-abc123').subscribe((e) => (recibido = e));

    const peticion = http.expectOne(
      (r) => r.url === `${api}/pagos/estado/` && r.params.get('referencia') === 'ref-abc123',
    );
    expect(peticion.request.method).toBe('GET');
    peticion.flush(estado);

    expect(recibido!.estado).toBe('aprobado');
  });
});
