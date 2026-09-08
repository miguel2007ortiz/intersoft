import { DatosCheckoutPasarela } from '../models/tienda.model';
import { CLAVE_REFERENCIA_PAGO, urlCheckoutPasarela } from './pasarela.util';

const DATOS: DatosCheckoutPasarela = {
  url: 'https://checkout.wompi.co/p/',
  public_key: 'pub_test_llave',
  currency: 'COP',
  amount_in_cents: 5000000,
  reference: 'ref-abc123',
  signature_integrity: 'firma-calculada-en-el-backend',
  redirect_url: 'http://localhost:4200/pago/retorno',
};

describe('urlCheckoutPasarela', () => {
  const parametros = (datos: DatosCheckoutPasarela) =>
    new URL(urlCheckoutPasarela(datos)).searchParams;

  it('apunta al checkout de la pasarela', () => {
    expect(urlCheckoutPasarela(DATOS).startsWith('https://checkout.wompi.co/p/?')).toBe(true);
  });

  it('usa los nombres de parametro que exige Wompi', () => {
    // Wompi los espera con guiones y con dos puntos en la firma; si se envian
    // con los nombres del backend (public_key, amount_in_cents) el checkout
    // se abre vacio y el comprador no puede pagar.
    const p = parametros(DATOS);
    expect(p.get('public-key')).toBe('pub_test_llave');
    expect(p.get('amount-in-cents')).toBe('5000000');
    expect(p.get('currency')).toBe('COP');
    expect(p.get('reference')).toBe('ref-abc123');
    expect(p.get('signature:integrity')).toBe('firma-calculada-en-el-backend');
    expect(p.get('redirect-url')).toBe('http://localhost:4200/pago/retorno');
  });

  it('omite la url de retorno cuando no esta configurada', () => {
    expect(parametros({ ...DATOS, redirect_url: '' }).has('redirect-url')).toBe(false);
  });

  it('codifica los valores con caracteres especiales', () => {
    const p = parametros({ ...DATOS, reference: 'ref con espacio&raro' });
    expect(p.get('reference')).toBe('ref con espacio&raro');
  });

  it('no transporta secretos', () => {
    // Solo la llave publica y una firma ya calculada pueden viajar en la URL.
    const url = urlCheckoutPasarela(DATOS);
    expect(url).not.toContain('prv_');
    expect(url).not.toContain('integrity_secret');
    expect(url).not.toContain('events_secret');
  });

  it('expone una clave estable para guardar la referencia', () => {
    expect(CLAVE_REFERENCIA_PAGO).toBe('intersoft.pago.referencia');
  });
});
