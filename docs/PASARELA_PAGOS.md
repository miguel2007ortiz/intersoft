# Pasarela de pago (Wompi)

Cómo cobra InterSoft, qué cambia al pasar del mock al proveedor real y cómo
probarlo contra el sandbox.

---

## Dos modos

El adaptador `backend/core/services/pasarela_adapter.py` sigue el mismo patrón
que el de la DIAN: una variable de entorno decide si se sale a internet.

| `PASARELA_MOCK` | Proveedor | Cuándo resuelve el cobro |
| --- | --- | --- |
| `True` (default) | mock local | En la misma petición del checkout |
| `False` | Wompi | Después, por webhook |

El mock aprueba siempre y de forma determinista: la misma clave de idempotencia
produce el mismo `transaccion_id`. Sirve para desarrollo, demo y para los tests
que no tratan de la pasarela.

---

## Por qué el cobro real es asíncrono

Wompi no permite cobrar con una sola llamada de servidor. `POST /transactions`
exige un `payment_method.token` y un `acceptance_token`, y ambos requieren que
el comprador intervenga: datos de tarjeta y aceptación de términos. Por eso el
cobro real tiene tres tramos y el resultado no cabe en la respuesta del
checkout.

```
1. POST /api/tienda/checkout/
   El backend reserva stock, firma el enlace del Web Checkout
   y responde 202 PAGO_PENDIENTE con datos_checkout.

2. El navegador va a checkout.wompi.co
   El comprador paga. Wompi lo devuelve a WOMPI_REDIRECT_URL.

3. POST /api/tienda/pagos/webhook/wompi/
   Wompi notifica transaction.updated. El backend confirma la venta
   o revierte la reserva.
```

Entre el paso 1 y el 3 la venta queda en `estado_pago='pendiente'` y el stock
sigue reservado. Ninguna venta pasa a `aprobado` sin que la pasarela lo haya
confirmado: la URL de retorno la controla el navegador, así que creerle sería
dejar que el comprador se diera por pagado solo.

---

## Los dos secretos

Wompi usa dos secretos distintos para dos firmas distintas. Confundirlos es el
error típico de integración.

**`WOMPI_INTEGRITY_SECRET`** — firma de integridad. La calcula el comercio y
viaja en el enlace del Web Checkout. Impide que el comprador edite el monto o
la referencia en la URL.

```
SHA256(referencia + monto_en_centavos + moneda + secreto_integridad)
```

**`WOMPI_EVENTS_SECRET`** — firma de eventos. La calcula Wompi y viaja en el
webhook. Prueba que el evento viene de Wompi y no de un tercero.

```
SHA256(valores de signature.properties + timestamp + secreto_eventos)
```

Sin `WOMPI_EVENTS_SECRET` el webhook responde 503 y no procesa nada. Un webhook
sin secreto es un endpoint público capaz de marcar ventas como pagadas, así que
es preferible que se caiga a que acepte eventos sin firmar.

---

## Controles del webhook

El endpoint es público a propósito: lo llama Wompi, no el navegador, y por eso
no lleva sesión ni JWT. Su control de acceso es la firma. Aplica cuatro
comprobaciones, en orden:

1. **Secreto configurado.** Sin él, 503 y no se toca nada.
2. **Firma válida.** Se valida el checksum del cuerpo (o la cabecera
   `X-Event-Checksum`) contra el secreto de eventos. Sin firma válida, 401.
3. **Reconsulta a la API.** La firma solo cubre los campos listados en
   `signature.properties`, así que el resto del cuerpo no es de fiar. Se
   consulta `GET /transactions/{id}` y esa respuesta manda sobre el cuerpo. Si
   la reconsulta no está disponible se usa el cuerpo ya validado.
4. **Cuadre de monto.** Se compara lo notificado con lo reservado. Si no
   coincide, 409 y la venta queda pendiente para revisión manual.

**Idempotencia.** Wompi reenvía el mismo evento hasta recibir un 2xx. Confirmar
o revertir dos veces descuadraría el inventario, así que ambas operaciones
bloquean el intento y solo actúan si sigue `pendiente`. Un evento repetido
recibe 200 `YA_PROCESADO`. Un evento tardío que contradice a uno ya aplicado
tampoco deshace nada.

---

## Endpoints

| Método y ruta | Auth | Para qué |
| --- | --- | --- |
| `POST /api/tienda/checkout/` | JWT | Reserva y arranca el cobro |
| `GET /api/tienda/pagos/estado/?referencia=` | JWT | Estado real del intento |
| `POST /api/tienda/pagos/webhook/wompi/` | firma | Notificación de Wompi |

La consulta de estado está siempre acotada al usuario autenticado. La
referencia se deriva del carrito y es adivinable, así que sin ese filtro un
comprador podría leer el pago de otro.

### Códigos de respuesta del checkout

| Código | HTTP | Significado |
| --- | --- | --- |
| `EXITO` | 201 | Cobrado y confirmado (modo mock) |
| `PAGO_PENDIENTE` | 202 | Hay que ir a pagar a la pasarela |
| `PAGO_RECHAZADO` | 402 | Rechazado; reserva revertida |
| `PAGO_EN_CURSO` | 409 | Ya hay un cobro en curso con esa clave |
| `STOCK_INSUFICIENTE` | 400 | No se llamó a la pasarela |

---

## Probar contra el sandbox

1. Crea una cuenta de comercio en Wompi y copia del panel las llaves de
   sandbox: pública, privada, secreto de integridad y secreto de eventos.

2. Complétalas en tu `.env` (la plantilla está en `backend/.env.example`):

   ```
   PASARELA_MOCK=False
   WOMPI_SANDBOX=True
   WOMPI_PUBLIC_KEY=pub_test_...
   WOMPI_PRIVATE_KEY=prv_test_...
   WOMPI_INTEGRITY_SECRET=test_integrity_...
   WOMPI_EVENTS_SECRET=test_events_...
   WOMPI_REDIRECT_URL=http://localhost:4200/pago/retorno
   ```

3. Expón el backend a internet. Wompi tiene que poder alcanzar el webhook, y
   `localhost` no le sirve. Con ngrok:

   ```
   ngrok http 8000
   ```

4. Registra la URL del webhook en el panel de Wompi:

   ```
   https://TU-SUBDOMINIO.ngrok.io/api/tienda/pagos/webhook/wompi/
   ```

5. Compra algo en la tienda. El navegador sale a Wompi, pagas con una tarjeta
   de prueba del sandbox y vuelves a `/pago/retorno`, que consulta el estado
   hasta que el webhook lo resuelva.

Sin el paso 3 el pago se queda en pendiente para siempre: el comprador paga,
pero la notificación nunca llega y la venta no se confirma.

---

## Tests

```
cd backend
python manage.py test core.tests_fase4 core.tests_pasarela --settings=intersoft.test_settings
```

Cubren la firma de integridad y su orden de concatenación, la conversión a
centavos con `Decimal`, el checkout que responde 202 sin dar nada por pagado,
los cuatro controles del webhook, la idempotencia frente a reintentos y el
aislamiento de la consulta de estado entre compradores.

Ninguno sale a la red: la única llamada saliente posible se parchea o se deja
sin credenciales a propósito.
