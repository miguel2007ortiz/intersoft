"""
Adaptador mock del servicio web de la DIAN.

Configuracion por variable de entorno:
- DIAN_MOCK=True (default): simula respuestas de la DIAN.
- DIAN_MOCK=False: lanza error indicando que las credenciales reales
  aun no estan configuradas.

En el futuro, reemplazar la logica interna con la integracion
SOAP/REST real contra el web service de la DIAN.
"""

import hashlib
import os
import random
from dataclasses import dataclass


@dataclass
class RespuestaDIAN:
    """Respuesta estandar del adaptador DIAN."""
    aprobada: bool
    cufe: str = ''
    mensaje: str = ''
    codigo_error: str = ''
    comprobante_pdf: str = ''
    comprobante_xml: str = ''


def _generar_cufe(datos: dict) -> str:
    """Genera un CUFE simulado a partir de los datos de la venta."""
    cadena = (
        f"{datos.get('numero_factura', '')}"
        f"{datos.get('fecha', '')}"
        f"{datos.get('nit_empresa', '')}"
        f"{datos.get('cliente_doc', '')}"
        f"{datos.get('total', '')}"
        f"{random.randint(100000, 999999)}"
    )
    return hashlib.sha256(cadena.encode()).hexdigest().upper()[:60]


def _generar_pdf_simulado(numero_factura: str, cliente: str, total: str) -> str:
    """Genera contenido PDF simulado (en produccion seria un archivo real)."""
    return (
        f"FACTURA ELECTRONICA - {numero_factura}\n"
        f"Cliente: {cliente}\n"
        f"Total: ${total}\n"
        f"[Documento generado por DIAN Mock]"
    )


def _generar_xml_simulado(numero_factura: str, datos: dict) -> str:
    """Genera XML simulado del comprobante."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<FacturaElectronica>\n'
        f'  <Numero>{numero_factura}</Numero>\n'
        f'  <Fecha>{datos.get("fecha", "")}</Fecha>\n'
        f'  <Cliente>{datos.get("cliente_nombre", "")}</Cliente>\n'
        f'  <Total>{datos.get("total", "")}</Total>\n'
        '</FacturaElectronica>'
    )


def enviar_factura(datos_venta: dict) -> RespuestaDIAN:
    """Envia un comprobante a la DIAN para validacion.

    Args:
        datos_venta: numero_factura, fecha, nit_empresa, cliente_nombre,
            cliente_doc, cliente_email, subtotal, descuento, total, detalles.

    Returns:
        RespuestaDIAN con el resultado.
    """
    mock_habilitado = os.environ.get('DIAN_MOCK', 'True').lower() == 'true'

    if not mock_habilitado:
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Servicio DIAN no configurado. '
                    'Configura DIAN_MOCK=True o establece credenciales reales.',
            codigo_error='SIN_CREDENCIALES',
        )

    if not datos_venta.get('cliente_doc'):
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Rechazado: cliente sin documento de identificacion.',
            codigo_error='DATOS_INVALIDOS',
        )

    if not datos_venta.get('total') or float(str(datos_venta.get('total', 0))) <= 0:
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Rechazado: total de la factura es cero o invalido.',
            codigo_error='MONTO_INVALIDO',
        )

    # Simular fallo del servicio (10% de las veces)
    if random.randint(1, 10) == 1:
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Servicio DIAN temporalmente no disponible.',
            codigo_error='SERVICIO_INDISPONIBLE',
        )

    cufe = _generar_cufe(datos_venta)
    pdf = _generar_pdf_simulado(
        datos_venta.get('numero_factura', ''),
        datos_venta.get('cliente_nombre', ''),
        datos_venta.get('total', '0'),
    )
    xml = _generar_xml_simulado(
        datos_venta.get('numero_factura', ''),
        datos_venta,
    )

    return RespuestaDIAN(
        aprobada=True,
        cufe=cufe,
        mensaje='Factura aprobada por la DIAN.',
        comprobante_pdf=pdf,
        comprobante_xml=xml,
    )


def enviar_nota_credito(datos_nota: dict) -> RespuestaDIAN:
    """Envia una nota credito a la DIAN para validacion.

    Args:
        datos_nota: numero_nota, numero_factura_original, fecha,
            nit_empresa, cliente_doc, total, motivo.

    Returns:
        RespuestaDIAN con el resultado.
    """
    mock_habilitado = os.environ.get('DIAN_MOCK', 'True').lower() == 'true'

    if not mock_habilitado:
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Servicio DIAN no configurado.',
            codigo_error='SIN_CREDENCIALES',
        )

    if not datos_nota.get('motivo'):
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Rechazado: motivo de nota credito requerido.',
            codigo_error='DATOS_INVALIDOS',
        )

    # Simular fallo (5%)
    if random.randint(1, 20) == 1:
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Servicio DIAN temporalmente no disponible.',
            codigo_error='SERVICIO_INDISPONIBLE',
        )

    cufe_nota = _generar_cufe({
        'numero_factura': datos_nota.get('numero_nota', ''),
        'fecha': datos_nota.get('fecha', ''),
        'nit_empresa': datos_nota.get('nit_empresa', ''),
        'cliente_doc': datos_nota.get('cliente_doc', ''),
        'total': datos_nota.get('total', 0),
    })

    return RespuestaDIAN(
        aprobada=True,
        cufe=cufe_nota,
        mensaje='Nota credito aprobada por la DIAN.',
    )
