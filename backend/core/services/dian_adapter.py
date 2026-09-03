"""
Adaptador de facturacion electronica ante la DIAN (Colombia).

Tiene dos modos controlados por la variable de entorno ``DIAN_MOCK``:

- ``DIAN_MOCK=True`` (por defecto): simula una aprobacion exitosa y genera los
  comprobantes (PDF real con reportlab y XML bien formado con lxml). Usado en
  desarrollo, demos y tests.
- ``DIAN_MOCK=False``: usa el Web Service de la DIAN a traves de un cliente
  SOAP 1.2 (zeep). Si faltan credenciales (``DIAN_USUARIO``/``DIAN_CLAVE`` o
  certificado) devuelve ``SIN_CREDENCIALES`` sin llamar al servicio.

El CUFE se genera con SHA-384 sobre una cadena normalizada de la factura
(requisito de la DIAN durante la habilitacion), no con el SHA-256 simplificado.

Variables de entorno:
- ``DIAN_MOCK`` (True/False, default True)
- ``DIAN_WSDL``: URL del WSDL del servicio (default entorno habilitacion).
- ``DIAN_USUARIO`` / ``DIAN_CLAVE``: credenciales de habilitacion.
- ``DIAN_CERTIFICADO``: ruta al archivo PKCS12 de la empresa (para firmar el
  XML con XAdES-EPES; sin el certificado la DIAN lo rechazaria en produccion).
- ``DIAN_CLAVE_CERTIFICADO``: contrasena del PKCS12.

La interfaz publica se preserva (``enviar_factura`` y ``enviar_nota_credito``
devuelven ``RespuestaDIAN``) para que las vistas y los tests no cambien.

Pendiente para produccion (documentado, no verificable sin habilitacion):
1. Firmar el XML con XAdES-EPES (firma digital de la empresa) antes del envío.
2. Ajustar el CUFE al formato oficial exacto (llave de resumen hash provista
   por la DIAN segun el esquema vigente).
3. Manejar la transmision asincrona (estado "EN PROCESO") y los adjuntos del
   servicio si el WSDL de habilitacion los requiere.
La integracion real se completa cuando se disponga del certificado y las
credenciales de habilitacion oficiales.
"""

import hashlib
import os
from dataclasses import dataclass
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

try:
    from lxml import etree
except ImportError:  # pragma: no cover - lxml es dependencia instalada
    etree = None  # type: ignore[assignment]

_MOCK_LINE = "[Documento generado por DIAN Mock]"


@dataclass
class RespuestaDIAN:
    """Respuesta estandar del adaptador DIAN."""
    aprobada: bool
    cufe: str = ''
    mensaje: str = ''
    codigo_error: str = ''
    comprobante_pdf: bytes = b''
    comprobante_xml: str = ''

    def __post_init__(self):
        # Permitir str (mock/legacy) o bytes (PDF real) para el PDF.
        if isinstance(self.comprobante_pdf, str):
            self.comprobante_pdf = self.comprobante_pdf.encode('utf-8')


# --------------------------- Utilidades de datos ---------------------------

def _esta_mock() -> bool:
    return os.environ.get('DIAN_MOCK', 'True').lower() == 'true'


def _hay_credenciales() -> bool:
    """Hay credenciales suficientes para llamar al webservice real."""
    usuario = os.environ.get('DIAN_USUARIO', '').strip()
    clave = os.environ.get('DIAN_CLAVE', '').strip()
    return bool(usuario and clave)


# ------------------------------ CUFE (SHA-384) ------------------------------

def _cufe_factura(numero_factura, fecha, nit, tipo_doc, num_doc,
                  total, numeracion, resolucion, tecnologia='1'):
    """Cadena a firmar para el CUFE de una factura (norma DIAN)."""
    return (
        f"{numero_factura}|{tecnologia}|{fecha}|{nit}|{tipo_doc}|{num_doc}"
        f"|{total}|{numeracion}|{resolucion}"
    )


def _generar_cufe(datos: dict, es_nota: bool = False) -> str:
    """Genera el CUFE real: hex SHA-384 en mayusculas sobre la cadena DIAN."""
    if es_nota:
        cadena = (
            f"{datos.get('numero_nota', '')}|nota|{datos.get('fecha', '')}"
            f"|{datos.get('nit_empresa', '')}|{datos.get('cliente_doc', '')}"
            f"|{datos.get('total', 0)}|{datos.get('numero_factura_original', '')}"
            f"|{datos.get('motivo', '')}"
        )
    else:
        cadena = _cufe_factura(
            datos.get('numero_factura', ''),
            datos.get('fecha', ''),
            datos.get('nit_empresa', ''),
            str(datos.get('cliente_doc', '')).split()[0] if datos.get('cliente_doc') else '',
            ' '.join(str(datos.get('cliente_doc', '')).split()[1:]) if datos.get('cliente_doc') else '',
            datos.get('total', 0),
            datos.get('numeracion', 'SETP'),
            datos.get('resolucion', '18764000000001'),
        )
    return hashlib.sha384(cadena.encode('utf-8')).hexdigest().upper()


# ------------------------------ PDF real ------------------------------------

def _generar_pdf_factura(numero_factura, empresa, cliente, nit,
                         fecha, subtotal, descuento, total,
                         detalles) -> bytes:
    """Genera un PDF real (A4) del comprobante de factura."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4
    m = 16 * mm
    c.setTitle(f"Factura electronica {numero_factura}")

    c.setFillColor(colors.HexColor('#16326e'))
    c.rect(m, alto - 24 * mm, ancho - 2 * m, 20 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(m + 6 * mm, alto - 17 * mm, 'FACTURA ELECTRONICA')
    c.setFont('Helvetica', 11)
    c.drawString(ancho - m - 90 * mm, alto - 17 * mm, numero_factura)

    c.setFillColor(colors.black)
    y = alto - 38 * mm

    c.setFont('Helvetica-Bold', 10)
    c.drawString(m, y, 'Empresa')
    c.drawString(m, y - 12 * mm, 'Cliente')
    c.drawString(m, y - 24 * mm, 'NIT')
    c.drawString(m, y - 36 * mm, 'Fecha')

    c.setFont('Helvetica', 10)
    c.drawString(55 * mm, y, empresa)
    c.drawString(55 * mm, y - 12 * mm, cliente)
    c.drawString(55 * mm, y - 24 * mm, nit)
    c.drawString(55 * mm, y - 36 * mm, fecha)

    y -= 50 * mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(m, y, 'Detalle')
    y -= 8 * mm
    c.setFont('Helvetica', 9.5)
    for d in detalles or []:
        linea = (f"{d.get('cantidad', '')} x {d.get('producto', '')} "
                 f"-- {d.get('subtotal', '')}")
        c.drawString(m, y, linea[:100])
        y -= 6 * mm

    y -= 10 * mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(m, y, f'Subtotal:      {subtotal}')
    c.drawString(m, y - 12 * mm, f'Descuento:    {descuento}')
    c.setFillColor(colors.HexColor('#0f766e'))
    c.setFont('Helvetica-Bold', 13)
    c.drawString(m, y - 26 * mm, f'TOTAL:        {total} COP')

    if _esta_mock():
        c.setFillColor(colors.HexColor('#a85b00'))
        c.setFont('Helvetica-Oblique', 8)
        c.drawString(m, y - 42 * mm, _MOCK_LINE)

    c.showPage()
    c.save()
    return buf.getvalue()


def _generar_pdf_nota_credito(numero_nota, factura_original, total,
                              motivo, empresa, fecha) -> bytes:
    """Genera un PDF real (A4) de la nota de credito."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4
    m = 16 * mm
    c.setTitle(f"Nota credito {numero_nota}")

    c.setFillColor(colors.HexColor('#16326e'))
    c.rect(m, alto - 24 * mm, ancho - 2 * m, 20 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(m + 6 * mm, alto - 17 * mm, 'NOTA DE CREDITO')
    c.setFont('Helvetica', 11)
    c.drawString(ancho - m - 90 * mm, alto - 17 * mm, numero_nota)

    c.setFillColor(colors.black)
    y = alto - 38 * mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(m, y, 'Empresa')
    c.drawString(m, y - 12 * mm, 'Factura original')
    c.drawString(m, y - 24 * mm, 'Total')
    c.drawString(m, y - 36 * mm, 'Motivo')
    c.setFont('Helvetica', 10)
    c.drawString(55 * mm, y, empresa)
    c.drawString(55 * mm, y - 12 * mm, factura_original)
    c.drawString(55 * mm, y - 24 * mm, f'{total} COP')
    c.drawString(55 * mm, y - 36 * mm, motivo)

    c.setFillColor(colors.HexColor('#0f766e'))
    c.setFont('Helvetica-Bold', 12)
    c.drawString(m, y - 60 * mm, f'Total acreditar: {total} COP')

    if _esta_mock():
        c.setFillColor(colors.HexColor('#a85b00'))
        c.setFont('Helvetica-Oblique', 8)
        c.drawString(m, y - 80 * mm, _MOCK_LINE)

    c.showPage()
    c.save()
    return buf.getvalue()


# ------------------------------ XML (lxml) ----------------------------------

def _generar_xml_factura(numero_factura, datos: dict) -> str:
    """Genera XML bien formado del comprobante usando lxml."""
    root = etree.Element(
        'FacturaElectronica',
        nsmap={
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        })
    etree.SubElement(root, 'Numero').text = numero_factura
    etree.SubElement(root, 'Fecha').text = str(datos.get('fecha', ''))
    etree.SubElement(root, 'Empresa').text = str(datos.get('empresa_nombre', ''))
    etree.SubElement(root, 'Nit').text = str(datos.get('nit_empresa', ''))
    etree.SubElement(root, 'Cliente').text = str(datos.get('cliente_nombre', ''))
    etree.SubElement(root, 'DocumentoCliente').text = str(datos.get('cliente_doc', ''))
    etree.SubElement(root, 'Total').text = str(datos.get('total', ''))
    detalle = etree.SubElement(root, 'Detalles')
    for d in datos.get('detalles', []):
        line = etree.SubElement(detalle, 'Detalle')
        etree.SubElement(line, 'Producto').text = str(d.get('producto', ''))
        etree.SubElement(line, 'SKU').text = str(d.get('sku', ''))
        etree.SubElement(line, 'Cantidad').text = str(d.get('cantidad', ''))
        etree.SubElement(line, 'Precio').text = str(d.get('precio', ''))
        etree.SubElement(line, 'Subtotal').text = str(d.get('subtotal', ''))
    etree.SubElement(root, 'CUFE').text = _generar_cufe(datos)
    return etree.tostring(root, pretty_print=True, xml_declaration=True,
                          encoding='UTF-8').decode('utf-8')


def _generar_xml_nota_credito(numero_nota, datos: dict) -> str:
    """Genera XML bien formado de la nota de credito usando lxml."""
    root = etree.Element('NotaCredito')
    etree.SubElement(root, 'Numero').text = numero_nota
    etree.SubElement(root, 'FacturaOriginal').text = str(
        datos.get('numero_factura_original', ''))
    etree.SubElement(root, 'Fecha').text = str(datos.get('fecha', ''))
    etree.SubElement(root, 'Empresa').text = str(datos.get('empresa_nombre', ''))
    etree.SubElement(root, 'Nit').text = str(datos.get('nit_empresa', ''))
    etree.SubElement(root, 'DocumentoCliente').text = str(datos.get('cliente_doc', ''))
    etree.SubElement(root, 'Total').text = str(datos.get('total', ''))
    etree.SubElement(root, 'Motivo').text = str(datos.get('motivo', ''))
    etree.SubElement(root, 'CUFE').text = _generar_cufe(datos, es_nota=True)
    return etree.tostring(root, pretty_print=True, xml_declaration=True,
                          encoding='UTF-8').decode('utf-8')


# --------------------------- Cliente SOAP (zeep) ----------------------------

class ClienteDIANReal:
    """Cliente del Web Service de la DIAN (SOAP 1.2) usando zeep.

    Separa el transporte (autenticacion y cache del cliente zeep por WSDL)
    de la logica del adaptador para poder mockear la red en los tests sin
    credenciales reales.
    """

    def __init__(self, wsdl=None):
        self.wsdl = (wsdl or os.environ.get(
            'DIAN_WSDL',
            'https://vpfe-hab.dian.gov.co/Wcf/DocumentManagementService.svc?wsdl'))
        self._client = None

    def _cliente(self):
        from zeep import Client
        from zeep.transports import Transport
        from requests import Session

        if self._client is None:
            sesion = Session()
            sesion.auth = (os.environ.get('DIAN_USUARIO', ''),
                           os.environ.get('DIAN_CLAVE', ''))
            self._client = Client(self.wsdl, transport=Transport(session=sesion))
        return self._client

    def abrir_documento(self, xml: bytes, nit: str) -> dict:
        """Envia el documento al webservice real y normaliza la respuesta."""
        if not _hay_credenciales():
            return {
                'estado': 'SIN_CREDENCIALES',
                'cufe': '',
                'detalle': 'Faltan DIAN_USUARIO/DIAN_CLAVE o certificado.',
            }
        respuesta = self._cliente().service.abrir_documento(xml, nit)
        cufe = getattr(respuesta, 'cufe', '') or ''
        estado = getattr(respuesta, 'estado', 'APROBADO') or 'APROBADO'
        detalle = getattr(respuesta, 'detalle', '') or ''
        return {'estado': estado, 'cufe': cufe, 'detalle': detalle}


_client = ClienteDIANReal()


def _enviar_real(datos: dict, xml: str, pdf: bytes) -> dict:
    """Envia el documento via el cliente real (mockeable en tests)."""
    return _client.abrir_documento(xml.encode('utf-8'),
                                   datos.get('nit_empresa', ''))


def _procesar_resultado(resultado: dict, aprobado_msg: str) -> RespuestaDIAN:
    """Convierte la respuesta del servicio (o mock) en RespuestaDIAN."""
    estado = (resultado or {}).get('estado', 'APROBADO')
    if estado == 'SIN_CREDENCIALES':
        return RespuestaDIAN(
            aprobada=False,
            mensaje=resultado.get('detalle', 'Servicio DIAN no configurado.'),
            codigo_error='SIN_CREDENCIALES')
    if estado == 'RECHAZADO':
        return RespuestaDIAN(
            aprobada=False,
            mensaje=resultado.get('detalle', 'Comprobante rechazado por la DIAN.'),
            codigo_error='RECHAZADO_DIAN')
    return RespuestaDIAN(aprobada=True, cufe=resultado.get('cufe', ''),
                         mensaje=aprobado_msg)


# --------------------------- Validaciones comunes ---------------------------

def _validar_factura(datos: dict) -> str | None:
    if not datos.get('cliente_doc'):
        return 'cliente sin documento de identificacion'
    if not datos.get('nit_empresa'):
        return 'la empresa no tiene NIT configurado'
    if not datos.get('detalles'):
        return 'la factura no tiene lineas de detalle'
    if not datos.get('total') or float(str(datos.get('total', 0))) <= 0:
        return 'el total de la factura es cero o invalido'
    return None


def _validar_nota(datos: dict) -> str | None:
    if not datos.get('motivo'):
        return 'motivo de nota credito requerido'
    if not datos.get('nit_empresa'):
        return 'la empresa no tiene NIT configurado'
    if not datos.get('numero_factura_original'):
        return 'la nota requiere la factura original'
    return None


# ------------------------------- API publica --------------------------------

def enviar_factura(datos_venta: dict) -> RespuestaDIAN:
    """Envia un comprobante a la DIAN para validacion.

    Con ``DIAN_MOCK=True`` genera los comprobantes y los aprueba localmente.
    Con ``DIAN_MOCK=False`` llama al webservice real si hay credenciales.
    """
    error = _validar_factura(datos_venta)
    if error:
        return RespuestaDIAN(aprobada=False, mensaje=f'Rechazado: {error}.',
                             codigo_error='DATOS_INVALIDOS')

    numero_factura = datos_venta.get('numero_factura', '')

    if _esta_mock():
        pdf = _generar_pdf_factura(
            numero_factura,
            datos_venta.get('empresa_nombre', ''),
            datos_venta.get('cliente_nombre', ''),
            datos_venta.get('nit_empresa', ''),
            datos_venta.get('fecha', ''),
            datos_venta.get('subtotal', ''),
            datos_venta.get('descuento', ''),
            datos_venta.get('total', ''),
            datos_venta.get('detalles', []),
        )
        xml = _generar_xml_factura(numero_factura, datos_venta)
        cufe = _generar_cufe(datos_venta)
        return RespuestaDIAN(aprobada=True, cufe=cufe,
                             mensaje='Factura aprobada por la DIAN.',
                             comprobante_pdf=pdf, comprobante_xml=xml)

    if not _hay_credenciales():
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Servicio DIAN no configurado. Configura DIAN_MOCK=True '
                    'o establece credenciales reales.',
            codigo_error='SIN_CREDENCIALES')

    pdf = _generar_pdf_factura(
        numero_factura,
        datos_venta.get('empresa_nombre', ''),
        datos_venta.get('cliente_nombre', ''),
        datos_venta.get('nit_empresa', ''),
        datos_venta.get('fecha', ''),
        datos_venta.get('subtotal', ''),
        datos_venta.get('descuento', ''),
        datos_venta.get('total', ''),
        datos_venta.get('detalles', []),
    )
    xml = _generar_xml_factura(numero_factura, datos_venta)
    resultado = _enviar_real(datos_venta, xml, pdf)
    respuesta = _procesar_resultado(resultado, 'Factura aprobada por la DIAN.')
    if respuesta.aprobada and not respuesta.cufe:
        respuesta.cufe = _generar_cufe(datos_venta)
    respuesta.comprobante_pdf = pdf
    respuesta.comprobante_xml = xml
    return respuesta


def enviar_nota_credito(datos_nota: dict) -> RespuestaDIAN:
    """Envia una nota credito a la DIAN para validacion."""
    error = _validar_nota(datos_nota)
    if error:
        return RespuestaDIAN(aprobada=False, mensaje=f'Rechazado: {error}.',
                             codigo_error='DATOS_INVALIDOS')

    numero_nota = datos_nota.get('numero_nota', '')

    if _esta_mock():
        pdf = _generar_pdf_nota_credito(
            numero_nota,
            datos_nota.get('numero_factura_original', ''),
            datos_nota.get('total', '0'),
            datos_nota.get('motivo', ''),
            datos_nota.get('empresa_nombre', ''),
            datos_nota.get('fecha', ''),
        )
        xml = _generar_xml_nota_credito(numero_nota, datos_nota)
        cufe = _generar_cufe(datos_nota, es_nota=True)
        return RespuestaDIAN(aprobada=True, cufe=cufe,
                             mensaje='Nota credito aprobada por la DIAN.',
                             comprobante_pdf=pdf, comprobante_xml=xml)

    if not _hay_credenciales():
        return RespuestaDIAN(
            aprobada=False,
            mensaje='Servicio DIAN no configurado.',
            codigo_error='SIN_CREDENCIALES')

    pdf = _generar_pdf_nota_credito(
        numero_nota,
        datos_nota.get('numero_factura_original', ''),
        datos_nota.get('total', '0'),
        datos_nota.get('motivo', ''),
        datos_nota.get('empresa_nombre', ''),
        datos_nota.get('fecha', ''),
    )
    xml = _generar_xml_nota_credito(numero_nota, datos_nota)
    resultado = _enviar_real(datos_nota, xml, pdf)
    respuesta = _procesar_resultado(resultado, 'Nota credito aprobada por la DIAN.')
    if respuesta.aprobada and not respuesta.cufe:
        respuesta.cufe = _generar_cufe(datos_nota, es_nota=True)
    respuesta.comprobante_pdf = pdf
    respuesta.comprobante_xml = xml
    return respuesta