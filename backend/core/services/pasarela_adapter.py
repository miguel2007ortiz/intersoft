"""
Adaptador de pasarela de pago (marketplace InterSoft).

Sigue el patron de ``core/services/dian_adapter.py`` (DIAN): dos modos
controlados por la variable de entorno ``PASARELA_MOCK``.

- ``PASARELA_MOCK=True`` (default): simula el cobro de forma determinista y
  testeable. Incluye un modo que fuerza el rechazo (para probar el camino de
  error del checkout).
- ``PASARELA_MOCK=False``: usa el proveedor real **Wompi** (Grupo Bancolombia,
  solo COP) via su API REST. Si faltan credenciales devuelve
  ``SIN_CONFIGURACION`` sin llamar al servicio.

Idempotencia: el ``cobrar`` recibe una ``idempotencia_clave`` derivada del
carrito del comprador.

- En modo mock el ``transaccion_id`` se genera de forma determinista a partir
  de esa clave (dos intentos con la misma clave devuelven el mismo id).
- En modo real se usa esa clave como ``reference`` de la transaccion de Wompi;
  Wompi rechaza una ``reference`` duplicada, de modo que el reintento de un
  mismo carrito no crea una segunda transaccion.

Webhooks (Fase 4): Wompi notifica ``transaction.updated`` al endpoint
registrado. La firma se valida con ``validar_firma_webhook`` (SHA256 de los
valores de ``signature.properties`` + ``timestamp`` + event secret, sin
separadores).

Variables de entorno:
- ``PASARELA_MOCK`` (True/False, default True)
- ``PASARELA_PROVEEDOR``: 'mock' (hoy) | 'wompi'
- ``WOMPI_PUBLIC_KEY`` / ``WOMPI_PRIVATE_KEY``: llaves de comercio (sandbox o
  produccion).
- ``WOMPI_EVENTS_SECRET``: secreto de eventos para validar la firma de los
  webhooks (distinto de las llaves de API).
- ``WOMPI_SANDBOX`` (True/False, default True): elige el entorno de la API.
"""

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - requests es dependencia instalada
    requests = None  # type: ignore[assignment]


# Base URL Wompi segun entorno (sandbox vs produccion).
_WOMPI_BASE = {
    'sandbox': 'https://sandbox.wompi.co/v1',
    'produccion': 'https://production.wompi.co/v1',
}


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
    """
    aprobada: bool
    transaccion_id: str = ''
    estado: str = 'pendiente'
    mensaje: str = ''
    crudo: dict = field(default_factory=dict)
    pasarela: str = 'mock'


def _esta_mock() -> bool:
    return os.environ.get('PASARELA_MOCK', 'True').lower() == 'true'


def _tipo_cambio_dec(moneda: str) -> str | None:
    """Devuelve un valor informativo de moneda (hoy solo Wompi = COP)."""
    return moneda.upper()


def _generar_id(material: str) -> str:
    """Identificador determinista (solo modo mock)."""
    digest = hashlib.sha256(material.encode('utf-8')).hexdigest()[:24]
    return f"MOCK-{digest.upper()}"


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
    """Traduce el estado de la transaccion Wompi al estado normalizado."""
    mapeo = {
        'APPROVED': 'aprobado',
        'DECLINED': 'rechazado',
        'VOIDED': 'rechazado',
        'ERROR': 'rechazado',
        'PENDING': 'pendiente',
    }
    return mapeo.get(estado.upper(), 'pendiente')


def _cobrar_wompi(
    monto: Any,
    moneda: str,
    metodo_pago: str,
    referencia: str,
    idempotencia_clave: str,
) -> RespuestaPago:
    """Cobra en Wompi (Fase 4). Usa ``idempotencia_clave`` como ``reference``
    de la transaccion para que un reintento no cree un segundo cobro.

    En esta implementacion de referencia la transaccion se crea en estado
    PENDING (Wompi requiere flujos de aceptacion/token del lado del comercio
    que exceden el alcance de un checkout síncrono). El estado final se
    resuelve via webhook. Para no bloquear la venta de un primer pago demo sin
    canal de aceptacion, el codigo de integracion local registra la transaccion
    y devuelve una RespuestaPago 'pendiente'.
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

    if requests is None:  # pragma: no cover
        return RespuestaPago(
            aprobada=False, estado='rechazado', pasarela='wompi',
            mensaje='Libreria requests no disponible.',
            crudo={'error': 'NO_REQUESTS'})

    monto_centavos = int(round(float(monto) * 100))
    url = f"{_wompi_base_url()}/transactions"
    payload = {
        'amount_in_cents': monto_centavos,
        'currency': (moneda or 'COP').upper(),
        'reference': idempotencia_clave or referencia,
    }
    # En produccion Wompi exige un payment_method.token y el acceptance_token
    # presignado; ese flujo lo gestiona el comerce (widget/checkout web). Aqui
    # se deja declarado el contrato para el modo real y, por simplicidad de
    # esta fase, se envian los campos base requeridos por la API.
    headers = {'Authorization': f'Bearer {config["privada"]}',
               'Content-Type': 'application/json'}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
    except Exception:  # pragma: no cover - defensivo (red)
        return RespuestaPago(
            aprobada=False, estado='rechazado', pasarela='wompi',
            mensaje='No se pudo conectar con la pasarela Wompi (timeout de red).',
            crudo={'error': 'RED'})

    try:
        datos = resp.json()
    except Exception:  # pragma: no cover
        datos = {'no_json': resp.text[:500]}

    if resp.status_code not in (200, 201):
        return RespuestaPago(
            aprobada=False, estado='rechazado', pasarela='wompi',
            mensaje=(f"Wompi rechazo la transaccion (HTTP {resp.status_code})."),
            crudo={'error': 'WompiError', 'status': resp.status_code, **datos})

    transaccion = datos.get('data', {}).get('transaction', {}) or datos.get('data', {})
    transaccion_id = str(transaccion.get('id', ''))
    estado = _estado_normalizado_wompi(str(transaccion.get('status', 'PENDING')))
    aprobada = estado == 'aprobado'
    return RespuestaPago(
        aprobada=aprobada,
        transaccion_id=transaccion_id,
        estado=estado,
        pasarela='wompi',
        mensaje=f"Transaccion Wompi {estado}.",
        crudo=datos,
    )


def verificar_transaccion_wompi(transaccion_id: str) -> RespuestaPago | None:
    """Re-consulta una transaccion en Wompi (GET /transactions/{id}).

    Se usa en el webhook para no fiarse del cuerpo (la firma no cubre todos
    los campos) y para casos de pagos asincronos. Devuelve None si no hay
    credenciales o falla la red.
    """
    config = _wompi_config()
    if config is None or requests is None:
        return None
    url = f"{_wompi_base_url()}/transactions/{transaccion_id}"
    headers = {'Authorization': f'Bearer {config["privada"]}'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        datos = resp.json()
    except Exception:  # pragma: no cover - defensivo
        return None
    transaccion = datos.get('data', {}).get('transaction', {}) or datos.get('data', {})
    estado = _estado_normalizado_wompi(str(transaccion.get('status', 'PENDING')))
    return RespuestaPago(
        aprobada=estado == 'aprobado',
        transaccion_id=str(transaccion.get('id', transaccion_id)),
        estado=estado,
        pasarela='wompi',
        crudo=datos,
    )


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
       (en orden), desde la raiz del evento.
    2. Concatenar el campo ``timestamp`` (UNIX en ms) del evento.
    3. Concatenar el ``secret``.
    4. ``SHA256(cadena)`` (hex).
    5. Comparar (case-insensitive) con el checksum del evento / header.

    Devuelve True si el checksum calculado coincide con el provisto.
    """
    signature = evento.get('signature', {}) or {}
    propiedades = signature.get('properties', []) or []
    timestamp = str(evento.get('timestamp', ''))
    cadena = ''
    for prop in propiedades:
        cadena += _extraer_valor_por_ruta(evento.get('data', {}), prop)
    cadena += timestamp
    cadena += (secret or '')
    calculado = hashlib.sha256(cadena.encode('utf-8')).hexdigest()
    return hmac.compare_digest(calculado.lower(),
                               (checksum_provisto or '').lower())


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

    Devuelve siempre una ``RespuestaPago`` (nunca lanza).
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
