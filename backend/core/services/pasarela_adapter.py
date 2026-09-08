"""
Adaptador de pasarela de pago (marketplace InterSoft).

Sigue el patron de ``core/services/dian_adapter.py`` (DIAN): dos modos
controlados por la variable de entorno ``PASARELA_MOCK``.

- ``PASARELA_MOCK=True`` (default): simula el cobro de forma determinista y
  testeable. Incluye un modo que fuerza el rechazo (para probar el camino de
  error del checkout).
- ``PASARELA_MOCK=False``: usa el proveedor real **Wompi** (Grupo Bancolombia,
  solo COP). Si faltan credenciales devuelve ``SIN_CONFIGURACION`` sin llamar
  al servicio.

Flujo real (Fase 4) - Wompi Web Checkout
----------------------------------------
Wompi NO permite crear una transaccion aprobada con una sola llamada de
servidor: ``POST /transactions`` exige un ``payment_method.token`` y un
``acceptance_token`` que solo se obtienen con la interaccion del comprador
(datos de tarjeta, aceptacion de terminos). Por eso el cobro real es
asincrono y tiene tres tramos:

1. ``cobrar`` NO llama a la red: calcula la *firma de integridad* y devuelve
   una ``RespuestaPago`` en estado ``'pendiente'`` con ``datos_checkout``.
2. El frontend redirige al comprador al Web Checkout de Wompi con esos datos.
   Wompi cobra y devuelve al comprador a ``redirect_url``.
3. Wompi notifica ``transaction.updated`` al webhook del backend. Ahi se
   resuelve la venta (confirmar o revertir la reserva).

Devolver ``'pendiente'`` en vez de fingir una aprobacion es lo que mantiene
correcta la reserva de stock: las unidades quedan reservadas hasta que el
webhook confirme o rechace, y nunca se marca una venta como pagada sin que la
pasarela lo haya confirmado.

Firmas
------
Wompi usa DOS secretos distintos y DOS firmas distintas; mezclarlos es el
error tipico de integracion:

- *Firma de integridad* (``WOMPI_INTEGRITY_SECRET``): la calcula el comercio y
  viaja en el enlace del Web Checkout. Evita que el comprador manipule el
  monto o la referencia en la URL.
  ``SHA256(referencia + monto_en_centavos + moneda + secreto_integridad)``
- *Firma de eventos* (``WOMPI_EVENTS_SECRET``): la calcula Wompi y viaja en el
  webhook. Prueba que el evento viene de Wompi. Se valida con
  ``validar_firma_webhook_wompi``.

Idempotencia: ``cobrar`` recibe una ``idempotencia_clave`` derivada del
carrito del comprador.

- En modo mock el ``transaccion_id`` se genera de forma determinista a partir
  de esa clave (dos intentos con la misma clave devuelven el mismo id).
- En modo real se usa esa clave como ``reference`` de la transaccion de Wompi;
  Wompi rechaza una ``reference`` duplicada, de modo que el reintento de un
  mismo carrito no crea una segunda transaccion. Ademas es la clave con la que
  el webhook vuelve a encontrar el ``IntentoPago``.

Variables de entorno:
- ``PASARELA_MOCK`` (True/False, default True)
- ``WOMPI_PUBLIC_KEY`` / ``WOMPI_PRIVATE_KEY``: llaves de comercio (sandbox o
  produccion).
- ``WOMPI_INTEGRITY_SECRET``: secreto de integridad para firmar el enlace del
  Web Checkout.
- ``WOMPI_EVENTS_SECRET``: secreto de eventos para validar la firma de los
  webhooks (distinto de las llaves de API y del de integridad).
- ``WOMPI_SANDBOX`` (True/False, default True): elige el entorno de la API.
- ``WOMPI_REDIRECT_URL``: URL del frontend a la que Wompi devuelve al
  comprador tras pagar.
"""

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - requests es dependencia instalada
    requests = None  # type: ignore[assignment]


# Base URL de la API Wompi segun entorno (sandbox vs produccion).
_WOMPI_BASE = {
    'sandbox': 'https://sandbox.wompi.co/v1',
    'produccion': 'https://production.wompi.co/v1',
}

# Web Checkout (la pagina de pago a la que se redirige al comprador).
_WOMPI_CHECKOUT_URL = 'https://checkout.wompi.co/p/'


@dataclass
class RespuestaPago:
    """Respuesta estandar del adaptador de pasarela.

    Equivalente a ``RespuestaDIAN`` para el dominio de pagos:

    - ``aprobada``: si el pago se aprobo.
    - ``transaccion_id``: identificador devuelto por la pasarela (se persiste
      en ``Venta.transaccion_id`` y se cruza con los webhooks).
    - ``estado``: estado normalizado ('pendiente' | 'aprobado' | 'rechazado').
    - ``mensaje``: texto legible del resultado.
    - ``crudo``: respuesta cruda de la pasarela (dict) para auditoria/debug.
    - ``pasarela``: nombre del proveedor ('mock' | 'wompi').
    - ``datos_checkout``: datos publicos para abrir el Web Checkout de la
      pasarela (solo en pagos asincronos). NUNCA contiene la llave privada ni
      los secretos: solo la llave publica y la firma ya calculada.
    """
    aprobada: bool
    transaccion_id: str = ''
    estado: str = 'pendiente'
    mensaje: str = ''
    crudo: dict = field(default_factory=dict)
    pasarela: str = 'mock'
    datos_checkout: dict = field(default_factory=dict)


def _esta_mock() -> bool:
    return os.environ.get('PASARELA_MOCK', 'True').lower() == 'true'


def _tipo_cambio_dec(moneda: str) -> str | None:
    """Devuelve un valor informativo de moneda (hoy solo Wompi = COP)."""
    return moneda.upper()


def _generar_id(material: str) -> str:
    """Identificador determinista (solo modo mock)."""
    digest = hashlib.sha256(material.encode('utf-8')).hexdigest()[:24]
    return f"MOCK-{digest.upper()}"


def a_centavos(monto: Any) -> int:
    """Convierte un monto en pesos a centavos enteros.

    Se pasa por ``Decimal`` (no por ``float``) porque los totales vienen de
    campos ``DecimalField``: con float, 1000.1 * 100 da 100009.99... y el
    redondeo binario terminaria firmando un monto distinto al cobrado.
    """
    return int((Decimal(str(monto)) * 100).quantize(Decimal('1')))


# ------------------------- Modo real: Wompi (Fase 4) -----------------------

def _wompi_base_url() -> str:
    sandbox = os.environ.get('WOMPI_SANDBOX', 'True').lower() == 'true'
    return _WOMPI_BASE['sandbox' if sandbox else 'produccion']


def _wompi_config() -> dict | None:
    """Valida que existan las credenciales de Wompi; None si faltan."""
    publica = os.environ.get('WOMPI_PUBLIC_KEY', '').strip()
    privada = os.environ.get('WOMPI_PRIVATE_KEY', '').strip()
    if not publica or not privada:
        return None
    return {'publica': publica, 'privada': privada}


def _estado_normalizado_wompi(estado: str) -> str:
    """Traduce el estado de la transaccion Wompi al estado normalizado.

    ``VOIDED`` (anulada) y ``ERROR`` se tratan como rechazo porque el efecto
    de negocio es el mismo: no hay dinero cobrado y hay que devolver el stock.
    """
    mapeo = {
        'APPROVED': 'aprobado',
        'DECLINED': 'rechazado',
        'VOIDED': 'rechazado',
        'ERROR': 'rechazado',
        'PENDING': 'pendiente',
    }
    return mapeo.get(estado.upper(), 'pendiente')


def firma_integridad_wompi(referencia: str, monto_centavos: int,
                           moneda: str, secreto: str) -> str:
    """Firma de integridad del enlace del Web Checkout.

    ``SHA256(referencia + monto_en_centavos + moneda + secreto)``, en ese
    orden y sin separadores. Wompi la recalcula al recibir al comprador y
    rechaza el enlace si el monto o la referencia fueron alterados.
    """
    cadena = f"{referencia}{monto_centavos}{moneda.upper()}{secreto}"
    return hashlib.sha256(cadena.encode('utf-8')).hexdigest()


def _cobrar_wompi(
    monto: Any,
    moneda: str,
    metodo_pago: str,
    referencia: str,
    idempotencia_clave: str,
) -> RespuestaPago:
    """Prepara un cobro real en Wompi (Web Checkout, asincrono).

    No hace ninguna llamada de red: construye y firma el enlace del Web
    Checkout y devuelve estado ``'pendiente'``. El estado definitivo llega por
    webhook (``transaction.updated``), que es la unica fuente que se acepta
    para dar una venta por pagada.

    Usa ``idempotencia_clave`` como ``reference`` para que un reintento del
    mismo carrito no genere un segundo cobro, y para que el webhook pueda
    reencontrar el ``IntentoPago``.
    """
    config = _wompi_config()
    if config is None:
        return RespuestaPago(
            aprobada=False,
            estado='rechazado',
            pasarela='wompi',
            mensaje=("Pasarela Wompi no configurada. Faltan WOMPI_PUBLIC_KEY/"
                     "WOMPI_PRIVATE_KEY. Usa PASARELA_MOCK=True mientras tanto."),
            crudo={'error': 'SIN_CONFIGURACION'},
        )

    secreto_integridad = os.environ.get('WOMPI_INTEGRITY_SECRET', '').strip()
    if not secreto_integridad:
        # Sin este secreto el enlace no se puede firmar y Wompi lo rechazaria
        # en el navegador del comprador. Es preferible fallar aqui, antes de
        # mandarlo a una pagina de pago rota.
        return RespuestaPago(
            aprobada=False,
            estado='rechazado',
            pasarela='wompi',
            mensaje=("Falta WOMPI_INTEGRITY_SECRET: no se puede firmar el "
                     "enlace de pago."),
            crudo={'error': 'SIN_SECRETO_INTEGRIDAD'},
        )

    moneda = (moneda or 'COP').upper()
    monto_centavos = a_centavos(monto)
    reference = idempotencia_clave or referencia
    firma = firma_integridad_wompi(reference, monto_centavos, moneda,
                                   secreto_integridad)

    return RespuestaPago(
        aprobada=False,
        transaccion_id='',      # lo asigna Wompi; llega en el webhook
        estado='pendiente',
        pasarela='wompi',
        mensaje=('Redirige al comprador al checkout de Wompi para completar '
                 'el pago.'),
        crudo={
            'reference': reference,
            'amount_in_cents': monto_centavos,
            'currency': moneda,
            'metodo_pago': metodo_pago,
        },
        datos_checkout={
            'url': _WOMPI_CHECKOUT_URL,
            'public_key': config['publica'],
            'currency': moneda,
            'amount_in_cents': monto_centavos,
            'reference': reference,
            'signature_integrity': firma,
            'redirect_url': os.environ.get('WOMPI_REDIRECT_URL', '').strip(),
        },
    )


def respuesta_desde_transaccion_wompi(transaccion: dict) -> RespuestaPago:
    """Construye una ``RespuestaPago`` desde el objeto ``transaction`` de Wompi.

    Es el unico punto donde se interpreta el vocabulario de Wompi (APPROVED,
    DECLINED...), tanto para el webhook como para la reconsulta por API.
    """
    estado = _estado_normalizado_wompi(str(transaccion.get('status', 'PENDING')))
    return RespuestaPago(
        aprobada=estado == 'aprobado',
        transaccion_id=str(transaccion.get('id', '')),
        estado=estado,
        pasarela='wompi',
        mensaje=f"Transaccion Wompi {estado}.",
        crudo=transaccion,
    )


def verificar_transaccion_wompi(transaccion_id: str) -> RespuestaPago | None:
    """Re-consulta una transaccion en Wompi (GET /transactions/{id}).

    Se usa en el webhook para no fiarse del cuerpo recibido: la firma de
    eventos solo cubre los campos listados en ``signature.properties``, asi
    que cualquier otro campo del cuerpo podria venir alterado. Preguntarle a
    Wompi por el id es la comprobacion autoritativa.

    Devuelve None si no hay credenciales o falla la red; en ese caso el
    llamador decide si se conforma con el cuerpo firmado.
    """
    config = _wompi_config()
    if config is None or requests is None:
        return None
    url = f"{_wompi_base_url()}/transactions/{transaccion_id}"
    headers = {'Authorization': f'Bearer {config["privada"]}'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        datos = resp.json()
    except Exception:  # pragma: no cover - defensivo (red)
        return None
    if resp.status_code != 200:
        return None
    transaccion = datos.get('data', {}).get('transaction', {}) or datos.get('data', {})
    respuesta = respuesta_desde_transaccion_wompi(transaccion)
    if not respuesta.transaccion_id:
        respuesta.transaccion_id = transaccion_id
    return respuesta


def _extraer_valor_por_ruta(datos: Any, ruta: str) -> str:
    """Extrae el valor referido por una ruta con puntos (ej. 'transaction.id')
    de la estructura del evento, resolviendo tambien mayusculas/minusculas
    para adaptarse a la variabilidad de Wompi."""
    partes = ruta.split('.')
    actual = datos
    for p in partes:
        if isinstance(actual, dict):
            if p in actual:
                actual = actual[p]
                continue
            # tolerancia: ruta 'transaction.amount_in_cents' vs 'amountInCents'
            coincidencia = next(
                (k for k in actual if k.lower() == p.lower()), None)
            if coincidencia is None:
                return ''
            actual = actual[coincidencia]
        else:
            return ''
    return actual if isinstance(actual, str) else str(actual)


def validar_firma_webhook_wompi(evento: dict, secret: str,
                                checksum_provisto: str) -> bool:
    """Valida la firma de un webhook de Wompi (SHA256, sin separadores).

    Algoritmo documentado por Wompi:
    1. Concatenar los valores de los campos listados en ``signature.properties``
       (en orden), leidos desde ``data``.
    2. Concatenar el campo ``timestamp`` del evento.
    3. Concatenar el ``secret`` de eventos.
    4. ``SHA256(cadena)`` (hex).
    5. Comparar (case-insensitive) con el checksum del evento / header.

    Devuelve True solo si el checksum calculado coincide con el provisto. Un
    evento sin ``signature.properties``, sin secreto o sin checksum no valida:
    se rechaza, nunca se acepta por omision.
    """
    if not secret or not checksum_provisto:
        return False
    signature = evento.get('signature', {}) or {}
    propiedades = signature.get('properties', []) or []
    if not propiedades:
        return False
    timestamp = str(evento.get('timestamp', ''))
    cadena = ''
    for prop in propiedades:
        cadena += _extraer_valor_por_ruta(evento.get('data', {}), prop)
    cadena += timestamp
    cadena += secret
    calculado = hashlib.sha256(cadena.encode('utf-8')).hexdigest()
    return hmac.compare_digest(calculado.lower(), checksum_provisto.lower())


def secreto_eventos_wompi() -> str:
    """Secreto de eventos configurado (cadena vacia si no hay)."""
    return os.environ.get('WOMPI_EVENTS_SECRET', '').strip()


# ------------------------------- Interfaz publica ---------------------------

def cobrar(
    monto: Any,
    moneda: str = 'COP',
    metodo_pago: str = 'tarjeta',
    referencia: str = '',
    idempotencia_clave: str = '',
    forzar_rechazo: bool = False,
) -> RespuestaPago:
    """Cobra un monto a traves de la pasarela (mock por defecto, Wompi real
    con ``PASARELA_MOCK=False``).

    Devuelve siempre una ``RespuestaPago`` (nunca lanza). Ojo: en modo real la
    respuesta es ``'pendiente'``, no aprobada; el llamador debe tratar ese
    tercer caso y esperar el webhook.
    """
    base = {
        'monto': str(monto),
        'moneda': _tipo_cambio_dec(moneda),
        'metodo_pago': metodo_pago,
        'referencia': referencia,
    }

    if not _esta_mock():
        return _cobrar_wompi(monto, moneda, metodo_pago, referencia,
                             idempotencia_clave)

    # --- Modo MOCK (determinista y testeable) ---
    material = idempotencia_clave or f"{referencia}|{monto}|{metodo_pago}"
    transaccion_id = _generar_id(material)

    if forzar_rechazo:
        return RespuestaPago(
            aprobada=False,
            transaccion_id=transaccion_id,
            estado='rechazado',
            mensaje='Pago rechazado (mock forzado).',
            crudo={**base, 'resuelto': 'RECHAZADO'},
        )

    return RespuestaPago(
        aprobada=True,
        transaccion_id=transaccion_id,
        estado='aprobado',
        mensaje='Pago aprobado (mock).',
        crudo={
            **base,
            'aprobado_en': datetime.now(timezone.utc).isoformat(),
            'resuelto': 'APROBADO',
        },
    )
