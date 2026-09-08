import { DatosCheckoutPasarela } from '../models/tienda.model';

/** Donde se guarda la referencia del pago mientras el comprador esta fuera
 * del sitio. Al volver de la pasarela solo llega el id de transaccion de
 * ella, no nuestra referencia, y sin referencia no se puede consultar el
 * estado del intento. */
export const CLAVE_REFERENCIA_PAGO = 'intersoft.pago.referencia';

/** Arma el enlace del Web Checkout de Wompi.
 *
 * Los nombres de los parametros los fija Wompi y usan guiones (y dos puntos
 * en la firma), por eso no coinciden con los campos que envia el backend.
 * La firma viene ya calculada del servidor: aqui solo se transporta. */
export function urlCheckoutPasarela(datos: DatosCheckoutPasarela): string {
  const parametros = new URLSearchParams({
    'public-key': datos.public_key,
    currency: datos.currency,
    'amount-in-cents': String(datos.amount_in_cents),
    reference: datos.reference,
    'signature:integrity': datos.signature_integrity,
  });
  if (datos.redirect_url) {
    parametros.set('redirect-url', datos.redirect_url);
  }
  return `${datos.url}?${parametros.toString()}`;
}
