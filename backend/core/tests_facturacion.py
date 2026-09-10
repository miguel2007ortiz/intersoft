"""Pruebas de la fase 6: facturacion electronica DIAN y notas credito.

Cubre los flujos de `views_facturacion.py`:
- Listado de facturas con filtros (estado, busqueda) y aislamiento por empresa.
- Generacion de factura: venta no encontrada, estado invalido, ya facturada,
  y las tres salidas del adaptador DIAN (aprobada / rechazada / fallida).
- Reenvio por correo (solo aprobadas) y reintento manual de facturas fallidas.
- Notas credito: validaciones de la venta, flujo aprobado (reverso de stock)
  y salidas rechazada/fallida con notificacion al administrador.
- Aislamiento multi-tenancy (EsPersonal + filtro por empresa).
"""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from cuentas.models import Perfil, Rol

from .models import (Cliente, DetalleVenta, Empresa, FacturaElectronica,
                     MovimientoInventario, NotaCredito, Notificacion, Producto,
                     Venta)
from .services.dian_adapter import RespuestaDIAN


class BaseFacturacionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Facturacion SA", nit="900222333")
        cls.otra = Empresa.objects.create(nombre="Otra SA", nit="900222334")
        cls.admin = User.objects.create_user(username="admon@test.co",
                                             email="admon@test.co",
                                             password="Clave12345")
        Perfil.objects.create(usuario=cls.admin, empresa=cls.empresa,
                              rol=Rol.de_nombre("ADMINISTRADOR"))
        cls.cliente = Cliente.objects.create(
            empresa=cls.empresa, nombre="Cliente Factura", tipo_documento="CC",
            numero_documento="3000000001", email="cliente@test.co",
            direccion="Calle 1", ciudad="Cali")
        cls.producto = Producto.objects.create(
            empresa=cls.empresa, nombre="Producto Factura", sku="FAC-1",
            precio="100000", stock=10, stock_minimo=1)

    @classmethod
    def api_como(cls, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    @classmethod
    def crear_usuario(cls, username, empresa, rol):
        usuario = User.objects.create_user(username=username, email=username,
                                           password="Clave12345")
        Perfil.objects.create(usuario=usuario, empresa=empresa,
                              rol=Rol.de_nombre(rol))
        return usuario

    @classmethod
    def crear_venta(cls, estado="completada", con_detalle=True):
        venta = Venta.objects.create(
            empresa=cls.empresa, cliente=cls.cliente, vendedor=cls.admin,
            subtotal="200000", descuento="0", total="200000", estado=estado)
        if con_detalle:
            DetalleVenta.objects.create(
                venta=venta, producto=cls.producto, cantidad=2,
                precio_unitario="100000")
        return venta

    @classmethod
    def crear_factura(cls, venta, estado="aprobada", intentos=0):
        return FacturaElectronica.objects.create(
            venta=venta, numero=f"FE-{venta.numero_factura}", estado=estado,
            cufe="CUFE-123" if estado == "aprobada" else "", intentos=intentos)


class FacturasListadoTest(BaseFacturacionTest):
    def test_anonimo_recibe_401(self):
        self.assertEqual(APIClient().get("/api/facturacion/").status_code, 401)

    def test_cliente_rol_recibe_403(self):
        cliente = self.crear_usuario("rolcli@test.co", self.empresa, "CLIENTE")
        self.assertEqual(self.api_como(cliente).get("/api/facturacion/").status_code, 403)

    def test_listado_vacio_y_con_filtro_estado(self):
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        api = self.api_como(self.admin)
        resp = api.get("/api/facturacion/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)
        resp = api.get("/api/facturacion/", {"estado": "pendiente"})
        self.assertEqual(resp.data["total"], 0)
        resp = api.get("/api/facturacion/", {"estado": "aprobada"})
        self.assertEqual(resp.data["total"], 1)
        self.assertEqual(resp.data["resultados"][0]["estado"], "aprobada")
        self.assertEqual(resp.data["resultados"][0]["numero"], f"FE-{venta.numero_factura}")

    def test_listado_busqueda_por_cliente(self):
        venta = self.crear_venta()
        self.crear_factura(venta, estado="rechazada")
        api = self.api_como(self.admin)
        resp = api.get("/api/facturacion/", {"busqueda": "Cliente Factura"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    def test_detalle_404_y_aislamiento_entre_empresas(self):
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="aprobada")
        otro_admin = self.crear_usuario("ajeno@test.co", self.otra, "ADMINISTRADOR")
        self.assertEqual(
            self.api_como(self.admin).get(f"/api/facturacion/{factura.id}/").status_code, 200)
        self.assertEqual(
            self.api_como(otro_admin).get(f"/api/facturacion/{factura.id}/").status_code, 404)
        self.assertEqual(
            self.api_como(self.admin).get(
                "/api/facturacion/00000000-0000-0000-0000-000000000000/").status_code, 404)
        # El listado ajeno no muestra facturas de la otra empresa.
        resp = self.api_como(otro_admin).get("/api/facturacion/")
        self.assertEqual(resp.data["total"], 0)


class GenerarFacturaTest(BaseFacturacionTest):
    def test_datos_invalidos_400(self):
        resp = self.api_como(self.admin).post("/api/facturacion/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "DATOS_INVALIDOS")

    def test_venta_no_encontrada_400(self):
        venta = self.crear_venta()
        otro_admin = self.crear_usuario("ajeno2@test.co", self.otra, "ADMINISTRADOR")
        resp = self.api_como(otro_admin).post(
            "/api/facturacion/", {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "VENTA_NO_ENCONTRADA")

    def test_venta_estado_invalido_400(self):
        venta = self.crear_venta(estado="anulada")
        resp = self.api_como(self.admin).post(
            "/api/facturacion/", {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "ESTADO_INVALIDO")

    def test_ya_facturada_400(self):
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        resp = self.api_como(self.admin).post(
            "/api/facturacion/", {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "YA_FACTURADA")
        self.assertIsNotNone(resp.data["factura_id"])

    @patch("core.views_facturacion.enviar_factura")
    def test_generar_aprobada_guarda_cufe_y_comprobantes(self, enviar):
        enviar.return_value = RespuestaDIAN(
            aprobada=True, cufe="CUFE-ABC123",
            comprobante_pdf=b"%PDF-1.4 mock", comprobante_xml="<xml/>")
        venta = self.crear_venta()
        resp = self.api_como(self.admin).post(
            "/api/facturacion/", {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        factura = FacturaElectronica.objects.get(venta=venta)
        self.assertEqual(factura.estado, "aprobada")
        self.assertEqual(factura.cufe, "CUFE-ABC123")
        self.assertTrue(factura.pdf)
        self.assertTrue(factura.xml)
        self.assertEqual(factura.numero, f"FE-{venta.numero_factura}")

    @patch("core.views_facturacion.enviar_factura")
    def test_generar_aprobada_pdf_como_texto_legacy(self, enviar):
        # Respaldo para PDFs que llegan como string (mock/legacy).
        enviar.return_value = RespuestaDIAN(
            aprobada=True, cufe="CUFE-TEXTO",
            comprobante_pdf="%PDF-1.4 legacy", comprobante_xml="<xml/>")
        venta = self.crear_venta()
        resp = self.api_como(self.admin).post(
            "/api/facturacion/", {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        factura = FacturaElectronica.objects.get(venta=venta)
        self.assertEqual(factura.estado, "aprobada")
        self.assertTrue(factura.pdf)

    @patch("core.views_facturacion.enviar_factura")
    def test_generar_rechazada_notifica_al_admin(self, enviar):
        enviar.return_value = RespuestaDIAN(
            aprobada=False, codigo_error="DATOS_INVALIDOS",
            mensaje="El documento del cliente es invalido.")
        venta = self.crear_venta()
        resp = self.api_como(self.admin).post(
            "/api/facturacion/", {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        factura = FacturaElectronica.objects.get(venta=venta)
        self.assertEqual(factura.estado, "rechazada")
        self.assertEqual(factura.motivo_rechazo, "El documento del cliente es invalido.")
        self.assertTrue(Notificacion.objects.filter(
            empresa=self.empresa, tipo="factura").exists())

    @patch("core.views_facturacion.enviar_factura")
    def test_generar_fallida_marca_intentos_y_notifica(self, enviar):
        enviar.return_value = RespuestaDIAN(
            aprobada=False, mensaje="Sin respuesta del servicio DIAN.")
        venta = self.crear_venta()
        resp = self.api_como(self.admin).post(
            "/api/facturacion/", {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        factura = FacturaElectronica.objects.get(venta=venta)
        self.assertEqual(factura.estado, "fallida")
        self.assertEqual(factura.intentos, 1)
        self.assertIsNotNone(factura.ultimo_intento)
        self.assertTrue(Notificacion.objects.filter(
            empresa=self.empresa, tipo="factura").exists())


class ReenviarFacturaTest(BaseFacturacionTest):
    def test_reenviar_404(self):
        self.assertEqual(
            self.api_como(self.admin).post(
                "/api/facturacion/00000000-0000-0000-0000-000000000000/reenviar/",
                {}, format="json").status_code, 404)

    def test_reenviar_solo_aprobadas(self):
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="pendiente")
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reenviar/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "FACTURA_NO_APROBADA")

    def test_reenviar_email_destino_invalido(self):
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="aprobada")
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reenviar/",
            {"email_destino": "no-es-un-correo"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "DATOS_INVALIDOS")

    def test_reenviar_sin_email_del_cliente(self):
        cliente_sin_email = Cliente.objects.create(
            empresa=self.empresa, nombre="Sin Correo", tipo_documento="CC",
            numero_documento="3000000002", email="")
        venta = Venta.objects.create(empresa=self.empresa, cliente=cliente_sin_email,
                                    vendedor=self.admin, total="100000",
                                    estado="completada")
        factura = self.crear_factura(venta, estado="aprobada")
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reenviar/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "SIN_EMAIL")

    def test_reenviar_mock_marca_envio(self):
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="aprobada")
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reenviar/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("MOCK", resp.data["detalle"])
        factura.refresh_from_db()
        self.assertTrue(factura.enviado_correo)
        self.assertIsNotNone(factura.enviado_correo_en)

    @patch("core.views_facturacion.enviar_factura")
    def test_reenviar_con_dian_mock_false(self, _enviar):
        import os
        with patch.dict(os.environ, {"DIAN_MOCK": "false"}, clear=False):
            venta = self.crear_venta()
            factura = self.crear_factura(venta, estado="aprobada")
            resp = self.api_como(self.admin).post(
                f"/api/facturacion/{factura.id}/reenviar/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertNotIn("MOCK", resp.data["detalle"])


class ReintentarFacturaTest(BaseFacturacionTest):
    def test_reintentar_404(self):
        self.assertEqual(
            self.api_como(self.admin).post(
                "/api/facturacion/00000000-0000-0000-0000-000000000000/reintentar/",
                {}, format="json").status_code, 404)

    def test_reintentar_estado_invalido(self):
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="aprobada")
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reintentar/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "ESTADO_INVALIDO")

    def test_reintentar_maximo_intentos(self):
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="fallida", intentos=5)
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reintentar/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "MAXIMO_INTENTOS")

    @patch("core.views_facturacion.enviar_factura")
    def test_reintentar_pasa_a_aprobada(self, enviar):
        enviar.return_value = RespuestaDIAN(aprobada=True, cufe="CUFE-RETRY",
                                            comprobante_pdf=b"%PDF-1.4",
                                            comprobante_xml="<xml/>")
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="fallida", intentos=1)
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reintentar/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        factura.refresh_from_db()
        self.assertEqual(factura.estado, "aprobada")
        self.assertEqual(factura.cufe, "CUFE-RETRY")
        self.assertEqual(factura.intentos, 2)
        self.assertEqual(factura.motivo_rechazo, "")

    @patch("core.views_facturacion.enviar_factura")
    def test_reintentar_rechazada(self, enviar):
        enviar.return_value = RespuestaDIAN(
            aprobada=False, codigo_error="DATOS_INVALIDOS",
            mensaje="Cupo agotado para el documento.")
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="fallida", intentos=1)
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reintentar/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        factura.refresh_from_db()
        self.assertEqual(factura.estado, "rechazada")
        self.assertEqual(factura.intentos, 2)

    @patch("core.views_facturacion.enviar_factura")
    def test_reintentar_sigue_fallida(self, enviar):
        enviar.return_value = RespuestaDIAN(aprobada=False, mensaje="Timeout.")
        venta = self.crear_venta()
        factura = self.crear_factura(venta, estado="fallida", intentos=2)
        resp = self.api_como(self.admin).post(
            f"/api/facturacion/{factura.id}/reintentar/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        factura.refresh_from_db()
        self.assertEqual(factura.estado, "fallida")
        self.assertEqual(factura.intentos, 3)
        self.assertEqual(factura.motivo_rechazo, "Timeout.")


class NotasCreditoTest(BaseFacturacionTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.empleado = cls.crear_usuario("empleado@test.co", cls.empresa, "EMPLEADO")

    def test_listado_requiere_personal(self):
        cliente = self.crear_usuario("rolcli2@test.co", self.empresa, "CLIENTE")
        self.assertEqual(
            self.api_como(cliente).get("/api/notas-credito/").status_code, 403)

    def test_listado_vacio(self):
        resp = self.api_como(self.admin).get("/api/notas-credito/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 0)

    def test_crear_datos_invalidos(self):
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": "00000000-0000-0000-0000-000000000000"},
            format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "DATOS_INVALIDOS")

    def test_crear_venta_no_encontrada(self):
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/",
            {"venta_id": "00000000-0000-0000-0000-000000000001", "motivo": "Devolucion"},
            format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "VENTA_NO_ENCONTRADA")

    def test_crear_venta_estado_no_completada(self):
        venta = self.crear_venta(estado="anulada")
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion"},
            format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "ESTADO_INVALIDO")

    def test_crear_sin_factura(self):
        venta = self.crear_venta()
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion"},
            format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "SIN_FACTURA")

    def test_crear_factura_no_aprobada(self):
        venta = self.crear_venta()
        self.crear_factura(venta, estado="pendiente")
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion"},
            format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "FACTURA_NO_APROBADA")

    def test_crear_ya_tiene_nota_activa(self):
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        NotaCredito.objects.create(
            venta_original=venta, numero=f"NC-{venta.numero_factura}",
            motivo="Devolucion", estado="pendiente")
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Segunda nota"},
            format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["codigo"], "YA_TIENE_NOTA")

    @patch("core.views_facturacion.enviar_nota_credito")
    def test_crear_aprobada_revierte_stock_y_anula_venta(self, enviar):
        enviar.return_value = RespuestaDIAN(
            aprobada=True, cufe="NC-CUFE-1",
            comprobante_pdf=b"%PDF-1.4 nota", comprobante_xml="<xml/>")
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        stock_inicial = self.producto.stock
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion"},
            format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        nota = NotaCredito.objects.get(venta_original=venta)
        self.assertEqual(nota.estado, "aprobada")
        self.assertEqual(nota.cufe_nota, "NC-CUFE-1")
        self.assertTrue(nota.reverso_stock)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "anulada")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, stock_inicial + 2)
        self.assertTrue(MovimientoInventario.objects.filter(
            producto=self.producto, tipo="entrada").exists())

    @patch("core.views_facturacion.enviar_nota_credito")
    def test_crear_rechazada_notifica(self, enviar):
        enviar.return_value = RespuestaDIAN(
            aprobada=False, codigo_error="DATOS_INVALIDOS", mensaje="Cupo incorrecto.")
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion"},
            format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        nota = NotaCredito.objects.get(venta_original=venta)
        self.assertEqual(nota.estado, "rechazada")
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "completada")
        self.assertTrue(Notificacion.objects.filter(
            empresa=self.empresa, tipo="factura").exists())

    @patch("core.views_facturacion.enviar_nota_credito")
    def test_crear_fallida_queda_pendiente_y_notifica(self, enviar):
        enviar.return_value = RespuestaDIAN(aprobada=False, mensaje="Sin conexion.")
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        resp = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion"},
            format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        nota = NotaCredito.objects.get(venta_original=venta)
        self.assertEqual(nota.estado, "pendiente")
        self.assertFalse(nota.reverso_stock)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "completada")
        self.assertTrue(Notificacion.objects.filter(
            empresa=self.empresa, tipo="factura").exists())

    @patch("core.views_facturacion.enviar_nota_credito")
    def test_crear_tras_rechazo_no_choca_con_numero_anterior(self, enviar):
        """Regresion: numero=NC-<factura> es unique=True; tras una nota
        rechazada, reintentar debia dar IntegrityError->500. Ahora la nueva
        nota suma un sufijo y el reintento se resuelve como 400/201 normal."""
        enviar.return_value = RespuestaDIAN(
            aprobada=False, codigo_error="DATOS_INVALIDOS", mensaje="Cupo incorrecto.")
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        primera = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion"},
            format="json")
        self.assertEqual(primera.status_code, 201, primera.content)
        self.assertEqual(primera.data["numero"], f"NC-{venta.numero_factura}")

        enviar.return_value = RespuestaDIAN(
            aprobada=True, cufe="NC-CUFE-2",
            comprobante_pdf=b"%PDF-1.4", comprobante_xml="<xml/>")
        segunda = self.api_como(self.admin).post(
            "/api/notas-credito/", {"venta_id": str(venta.id), "motivo": "Devolucion 2"},
            format="json")
        self.assertEqual(segunda.status_code, 201, segunda.content)
        self.assertEqual(segunda.data["numero"], f"NC-{venta.numero_factura}-2")
        self.assertEqual(NotaCredito.objects.filter(venta_original=venta).count(), 2)

    def test_detalle_404_y_aislamiento(self):
        venta = self.crear_venta()
        self.crear_factura(venta, estado="aprobada")
        nota = NotaCredito.objects.create(
            venta_original=venta, numero=f"NC-{venta.numero_factura}",
            motivo="Devolucion", estado="pendiente")
        otro_admin = self.crear_usuario("ajeno3@test.co", self.otra, "ADMINISTRADOR")
        self.assertEqual(
            self.api_como(self.admin).get(f"/api/notas-credito/{nota.id}/").status_code, 200)
        self.assertEqual(
            self.api_como(self.empleado).get(f"/api/notas-credito/{nota.id}/").status_code, 200)
        self.assertEqual(
            self.api_como(otro_admin).get(f"/api/notas-credito/{nota.id}/").status_code, 404)
        self.assertEqual(
            self.api_como(self.admin).get(
                "/api/notas-credito/00000000-0000-0000-0000-000000000000/").status_code, 404)