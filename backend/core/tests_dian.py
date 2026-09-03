"""D1: adaptador de facturacion electronica DIAN.

Cubre la integracion real preparada (sin credenciales oficiales):
- CUFE real (SHA-384) determinista, sin random.
- PDF real (reportlab) en formato binario %PDF.
- XML bien formado (lxml) que incluye el CUFE.
- Reglas de negocio (cliente_doc, nit, detalles, motivo) -> DATOS_INVALIDOS.
- DIAN_MOCK=False sin credenciales -> SIN_CREDENCIALES.
- DIAN_MOCK=False con credenciales: flujo del webservice real mockeando
  `_enviar_real` (APROBADO usa el CUFE de la DIAN; RECHAZADO -> RECHAZADO_DIAN).
- Nota de credito (mock) aprobada con PDF/XML reales.
"""

import os
from unittest.mock import patch

from django.test import SimpleTestCase

from lxml import etree

from .services.dian_adapter import (
    _generar_cufe,
    enviar_factura,
    enviar_nota_credito,
)

CERT = "900444001"
FECHA = "2026-09-03T10:00:00"
FACTURA = {
    "numero_factura": "FE-000001",
    "fecha": FECHA,
    "nit_empresa": CERT,
    "empresa_nombre": "Fase5 SA",
    "cliente_nombre": "Cliente Uno",
    "cliente_doc": "CC 9011111111",
    "cliente_email": "cli@test.co",
    "subtotal": "20000",
    "descuento": "0",
    "total": "20000",
    "numeracion": "SETP",
    "resolucion": "18764000000001",
    "detalles": [
        {"producto": "Producto F5", "sku": "F5-1", "cantidad": 2,
         "precio": "10000", "subtotal": "20000"},
    ],
}
NOTA = {
    "numero_nota": "NC-000001",
    "numero_factura_original": "FE-000001",
    "fecha": FECHA,
    "nit_empresa": CERT,
    "empresa_nombre": "Fase5 SA",
    "cliente_doc": "CC 9011111111",
    "total": "20000",
    "motivo": "Devolucion total",
}


class CufeSha384Test(SimpleTestCase):
    def test_es_sha384_en_mayusculas(self):
        cufe = _generar_cufe(FACTURA)
        self.assertEqual(len(cufe), 96, "SHA-384 son 96 hex en mayusculas")
        self.assertTrue(cufe.isupper())
        # Solo hex.
        self.assertTrue(all(ch in "0123456789ABCDEF" for ch in cufe))

    def test_determinista_sin_random(self):
        cufe1 = _generar_cufe(FACTURA)
        cufe2 = _generar_cufe(dict(FACTURA))
        self.assertEqual(cufe1, cufe2)

    def test_cambia_con_los_datos(self):
        distinta = _generar_cufe({**FACTURA, "total": "99999"})
        self.assertNotEqual(distinta, _generar_cufe(FACTURA))

    def test_nota_tiene_su_propia_cadena(self):
        cufe_nota = _generar_cufe(NOTA, es_nota=True)
        cufe_factura = _generar_cufe(FACTURA)
        self.assertEqual(len(cufe_nota), 96)
        self.assertNotEqual(cufe_nota, cufe_factura)


class PdfRealTest(SimpleTestCase):
    def test_pdf_binario_real(self):
        r = enviar_factura(dict(FACTURA))
        self.assertTrue(r.aprobada)
        self.assertEqual(r.comprobante_pdf[:5], b"%PDF-")
        # Firma del PDF (dict/trailer) presente: documento valido a grandes rasgos.
        self.assertIn(b"%%EOF", r.comprobante_pdf)

    def test_pdf_cambia_con_el_numero(self):
        r1 = enviar_factura(dict(FACTURA))
        r2 = enviar_factura({**FACTURA, "numero_factura": "FE-999999"})
        self.assertNotEqual(r1.comprobante_pdf, r2.comprobante_pdf)

    def test_pdf_nota_credito_real(self):
        r = enviar_nota_credito(dict(NOTA))
        self.assertTrue(r.aprobada)
        self.assertEqual(r.comprobante_pdf[:5], b"%PDF-")
        self.assertIn(b"%%EOF", r.comprobante_pdf)


class XmlRealTest(SimpleTestCase):
    def test_xml_parseable_y_con_cufe(self):
        r = enviar_factura(dict(FACTURA))
        cufe = _generar_cufe(FACTURA)
        root = etree.fromstring(r.comprobante_xml.encode("utf-8"))
        self.assertEqual(root.tag, "FacturaElectronica")
        self.assertEqual(root.findtext("CUFE"), cufe)
        self.assertEqual(root.findtext("Nit"), CERT)

    def test_xml_nota_credito(self):
        r = enviar_nota_credito(dict(NOTA))
        cufe = _generar_cufe(NOTA, es_nota=True)
        root = etree.fromstring(r.comprobante_xml.encode("utf-8"))
        self.assertEqual(root.tag, "NotaCredito")
        self.assertEqual(root.findtext("CUFE"), cufe)
        self.assertEqual(root.findtext("FacturaOriginal"), "FE-000001")


class ValidacionesTest(SimpleTestCase):
    def test_falta_cliente_doc(self):
        r = enviar_factura({**FACTURA, "cliente_doc": ""})
        self.assertFalse(r.aprobada)
        self.assertEqual(r.codigo_error, "DATOS_INVALIDOS")

    def test_falta_nit(self):
        r = enviar_factura({**FACTURA, "nit_empresa": ""})
        self.assertFalse(r.aprobada)
        self.assertEqual(r.codigo_error, "DATOS_INVALIDOS")

    def test_sin_detalles(self):
        r = enviar_factura({**FACTURA, "detalles": []})
        self.assertFalse(r.aprobada)
        self.assertEqual(r.codigo_error, "DATOS_INVALIDOS")

    def test_total_cero(self):
        r = enviar_factura({**FACTURA, "total": "0"})
        self.assertFalse(r.aprobada)
        self.assertEqual(r.codigo_error, "DATOS_INVALIDOS")

    def test_nota_sin_motivo(self):
        r = enviar_nota_credito({**NOTA, "motivo": ""})
        self.assertFalse(r.aprobada)
        self.assertEqual(r.codigo_error, "DATOS_INVALIDOS")


class CredencialesTest(SimpleTestCase):
    def test_mock_false_sin_credenciales(self):
        with patch.dict(os.environ, {"DIAN_MOCK": "False"}, clear=True):
            r = enviar_factura(dict(FACTURA))
            self.assertFalse(r.aprobada)
            self.assertEqual(r.codigo_error, "SIN_CREDENCIALES")

    def test_mock_true_por_defecto(self):
        with patch.dict(os.environ, {}, clear=True):
            r = enviar_factura(dict(FACTURA))
            self.assertTrue(r.aprobada)


class FlujoWebServiceTest(SimpleTestCase):
    def _base(self, **env):
        return patch.dict(os.environ, {
            "DIAN_MOCK": "False",
            "DIAN_USUARIO": "u",
            "DIAN_CLAVE": "c",
            **env,
        }, clear=True)

    def test_aprobado_usa_cufe_de_la_dian(self):
        with self._base(), \
             patch("core.services.dian_adapter._enviar_real",
                   return_value={"estado": "APROBADO", "cufe": "CUFER-REAL",
                                 "detalle": "ok"}):
            r = enviar_factura(dict(FACTURA))
            self.assertTrue(r.aprobada)
            self.assertEqual(r.cufe, "CUFER-REAL")

    def test_rechazado(self):
        with self._base(), \
             patch("core.services.dian_adapter._enviar_real",
                   return_value={"estado": "RECHAZADO", "cufe": "",
                                 "detalle": "Schema invalido"}):
            r = enviar_factura(dict(FACTURA))
            self.assertFalse(r.aprobada)
            self.assertEqual(r.codigo_error, "RECHAZADO_DIAN")

    def test_nota_recibida_en_webservice(self):
        with self._base(), \
             patch("core.services.dian_adapter._enviar_real",
                   return_value={"estado": "RECHAZADO", "cufe": "",
                                 "detalle": "NC rechazada"}):
            r = enviar_nota_credito(dict(NOTA))
            self.assertFalse(r.aprobada)
            self.assertEqual(r.codigo_error, "RECHAZADO_DIAN")