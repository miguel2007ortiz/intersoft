"""Fase 5: calidad del backend Django REST.

Cubre los huecos de cobertura y las correcciones de la fase 5:
- Shape uniforme de errores 400/403/404 (`{codigo, detalle, errores}`).
- Validacion de filtros de consulta (fechas, precios, categoria) -> 400.
- Validacion de `url_stream` de camaras.
- Paginacion acotada de listados (nunca ilimitada).
- Condiciones de carrera: VentaPOS, anulacion, checkout, facturacion.
- Anulacion de venta y reglas de negocio asociadas.
"""

import threading
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from cuentas.models import Perfil, Rol
from rest_framework.test import APIClient

from .models import (Camara, Carrito, CarritoItem, Categoria, Cliente, Cupon,
                     Empresa, FacturaElectronica, MovimientoInventario,
                     NotaCredito, Producto, Venta)


class BaseFase5Test(TestCase):
    """Empresa con admin, empleado, productos, cliente y venta lista."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")
        cls.empresa = Empresa.objects.create(nombre="Fase5 SA", nit="900444001")

        cls.admin = cls._cuenta("admin5@test.co", "ADMINISTRADOR")
        cls.empleado = cls._cuenta("emp5@test.co", "EMPLEADO")

        cls.categoria = Categoria.objects.create(empresa=cls.empresa,
                                                 nombre="Categoria F5")
        cls.producto = Producto.objects.create(
            empresa=cls.empresa, nombre="Producto F5", sku="F5-1",
            precio=10000, stock=10, stock_minimo=2, activo=True,
            categoria=cls.categoria)
        cls.cliente = Cliente.objects.create(
            empresa=cls.empresa, nombre="Cliente F5",
            tipo_documento="CC", numero_documento="9011111111")

    @classmethod
    def _cuenta(cls, email, rol):
        user = User.objects.create_user(username=email, email=email,
                                        password="Clave12345",
                                        first_name=email.split("@")[0])
        Perfil.objects.create(usuario=user, empresa=cls.empresa,
                              rol=Rol.de_nombre(rol))
        return user

    @classmethod
    def api_como(cls, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    def _crear_venta(self, cantidad=2, estado="completada"):
        return Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente,
            vendedor=self.empleado, subtotal=20000, descuento=0,
            total=20000, estado=estado)

    def _crear_detalle(self, venta, cantidad=2):
        from .models import DetalleVenta
        return DetalleVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=cantidad,
            precio_unitario=self.producto.precio)


# -------------------- Forma uniforme de errores ---------------------------

class FormaErroresTest(BaseFase5Test):
    def test_login_con_datos_invalidos_devuelve_shape_uniforme_400(self):
        api = self.api_como(self.admin)
        api.credentials()
        respuesta = api.post("/api/auth/login/",
                             {"email": "correo-invalido"},
                             format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("codigo", respuesta.data)
        self.assertIn("detalle", respuesta.data)
        self.assertIn("errores", respuesta.data)

    def test_cambiar_password_sin_datos_devuelve_shape_uniforme_400(self):
        api = self.api_como(self.empleado)
        respuesta = api.post("/api/auth/cambiar-password/",
                             {}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "DATOS_INVALIDOS")
        self.assertIn("errores", respuesta.data)

    def test_solicitar_recuperacion_sin_email_devuelve_400(self):
        respuesta = APIClient().post("/api/auth/password-reset/",
                                     {}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "DATOS_INVALIDOS")

    def test_venta_pos_con_cliente_ajeno_devuelve_400_shape(self):
        api = self.api_como(self.empleado)
        otra_empresa = Empresa.objects.create(nombre="Otra", nit="900444009")
        cliente_ajeno = Cliente.objects.create(
            empresa=otra_empresa, nombre="Ajeno",
            tipo_documento="CC", numero_documento="9099999999")
        respuesta = api.post("/api/ventas/pos/", {
            "cliente": str(cliente_ajeno.id),
            "detalles": [{"producto": str(self.producto.id), "cantidad": 1}],
            "metodo_pago": "efectivo",
            "descuento": "0",
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "CLIENTE_NO_ENCONTRADO")


# -------------------- Validacion de filtros -------------------------------

class FiltrosConsultaTest(BaseFase5Test):
    def test_catalogo_precio_invalido_devuelve_400(self):
        respuesta = APIClient().get("/api/tienda/catalogo/",
                                    {"precio_min": "abc"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "PRECIO_INVALIDO")

    def test_catalogo_categoria_invalida_devuelve_400(self):
        respuesta = APIClient().get("/api/tienda/catalogo/",
                                    {"categoria": "no-es-uuid"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "CATEGORIA_INVALIDA")

    def test_ventas_fecha_invalida_devuelve_400(self):
        api = self.api_como(self.empleado)
        respuesta = api.get("/api/ventas/", {"fecha_inicio": "01/09/2026"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "FECHA_INVALIDA")

    def test_ventas_fecha_valida_pasa(self):
        api = self.api_como(self.empleado)
        respuesta = api.get("/api/ventas/", {"fecha_inicio": "2026-09-01",
                                             "fecha_fin": "2026-09-30"})
        self.assertEqual(respuesta.status_code, 200)


class FiltrosDashboardTest(BaseFase5Test):
    def test_dashboard_fecha_invalida_devuelve_400(self):
        api = self.api_como(self.admin)
        respuesta = api.get("/api/dashboard/resumen/",
                            {"fecha_inicio": "no-valida"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "FILTROS_INVALIDOS")

    def test_dashboard_categoria_invalida_devuelve_400(self):
        api = self.api_como(self.admin)
        respuesta = api.get("/api/dashboard/ventas/", {"categoria": "x"})
        self.assertEqual(respuesta.status_code, 400)

    def test_reporte_fecha_invalida_devuelve_400(self):
        api = self.api_como(self.admin)
        respuesta = api.get("/api/reportes/vista/",
                            {"tipo": "ventas", "fecha_inicio": "bad"})
        self.assertEqual(respuesta.status_code, 400)


# -------------------- Validacion url_stream camaras -----------------------

class CamaraUrlTest(BaseFase5Test):
    def test_crear_camara_url_invalida_devuelve_400(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/camaras/", {
            "nombre": "Cam 1", "ubicacion": "Patio",
            "url_stream": "javascript:alert(1)",
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("url_stream", respuesta.data["errores"])

    def test_crear_camara_url_rtsp_valida(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/camaras/", {
            "nombre": "Cam 2", "ubicacion": "Patio",
            "url_stream": "rtsp://192.168.1.10:554/stream",
        }, format="json")
        self.assertEqual(respuesta.status_code, 201)

    def test_patch_camara_url_invalida_devuelve_400(self):
        camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 3")
        api = self.api_como(self.admin)
        respuesta = api.patch(f"/api/camaras/{camara.id}/",
                              {"url_stream": "ftp://x/y"}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_camara_sin_url_stream_es_valida(self):
        camara = Camara.objects.create(empresa=self.empresa, nombre="Cam 4")
        self.assertEqual(camara.url_stream, "")


# -------------------- Paginacion acotada ----------------------------------

class PaginacionAcotadaTest(BaseFase5Test):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for i in range(15):
            Producto.objects.create(
                empresa=cls.empresa, nombre=f"Prod {i}", sku=f"F5-L-{i}",
                precio=1000, stock=5, activo=True)

    def test_productos_sin_limite_explicito_devuelve_subconjunto_acotado(self):
        api = self.api_como(self.empleado)
        respuesta = api.get("/api/productos/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertLessEqual(len(respuesta.data["resultados"]), 200)

    def test_productos_respeta_limite_solicitado(self):
        api = self.api_como(self.empleado)
        respuesta = api.get("/api/productos/", {"limite": 5})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data["resultados"]), 5)

    def test_usuarios_devuelve_subconjunto_acotado(self):
        api = self.api_como(self.admin)
        respuesta = api.get("/api/seguridad/usuarios/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertLessEqual(len(respuesta.data["resultados"]), 200)


# -------------------- Anulacion de venta ----------------------------------

class AnulacionVentaTest(BaseFase5Test):
    def test_anular_venta_completa_revierte_stock(self):
        api = self.api_como(self.empleado)
        venta = self._crear_venta()
        self._crear_detalle(venta, cantidad=3)
        stock_inicial = self.producto.stock  # 10
        respuesta = api.post(f"/api/ventas/{venta.id}/anular/",
                             {"motivo": "Devolucion cliente"}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "anulada")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, stock_inicial + 3)

    def test_anular_venta_ya_anulada_devuelve_400(self):
        api = self.api_como(self.empleado)
        venta = self._crear_venta(estado="anulada")
        respuesta = api.post(f"/api/ventas/{venta.id}/anular/",
                             {"motivo": "otra vez"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "YA_ANULADA")

    def test_anular_sin_motivo_devuelve_400(self):
        api = self.api_como(self.empleado)
        venta = self._crear_venta()
        respuesta = api.post(f"/api/ventas/{venta.id}/anular/", {}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "DATOS_INVALIDOS")

    def test_anular_venta_facturada_dian_exige_nota_credito(self):
        api = self.api_como(self.empleado)
        venta = self._crear_venta()
        FacturaElectronica.objects.create(venta=venta, numero="FE-X",
                                          estado="aprobada")
        respuesta = api.post(f"/api/ventas/{venta.id}/anular/",
                             {"motivo": "intento"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "FACTURADA_DIAN")


# -------------------- Facturacion (evitar doble factura) ------------------

class FacturacionDobleTest(BaseFase5Test):
    def test_generar_factura_dos_veces_devuelve_ya_facturada(self):
        api = self.api_como(self.empleado)
        venta = self._crear_venta()
        r1 = api.post("/api/facturacion/", {"venta_id": str(venta.id)},
                      format="json")
        self.assertEqual(r1.status_code, 201)
        r2 = api.post("/api/facturacion/", {"venta_id": str(venta.id)},
                      format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.data["codigo"], "YA_FACTURADA")
        self.assertEqual(FacturaElectronica.objects.filter(venta=venta).count(), 1)

    def test_facturar_venta_no_completada_devuelve_400(self):
        api = self.api_como(self.empleado)
        venta = self._crear_venta(estado="pendiente")
        respuesta = api.post("/api/facturacion/",
                             {"venta_id": str(venta.id)}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["codigo"], "ESTADO_INVALIDO")


# -------------------- Carreras: POS ---------------------------------------

class ConcurrenciaPOS(TransactionTestCase):
    """Dos peticiones POS simultaneas no deben hacer oversell.

    Usa TransactionTestCase (commits reales entre threads) sobre MySQL para
    que los SELECT FOR UPDATE y el bloqueo de fila de empresa funcionen de
    verdad. Ejecuta dos ventas en paralelo; si ambas pidieran mas stock del
    disponible, una debe fallar.
    """
    reset_sequences = True

    def setUp(self):
        call_command("seed_roles")
        self.empresa = Empresa.objects.create(nombre="Conc SA", nit="900555001")
        self.user = User.objects.create_user(username="vp@test.co",
                                             email="vp@test.co",
                                             password="Clave12345")
        Perfil.objects.create(usuario=self.user, empresa=self.empresa,
                              rol=Rol.de_nombre("ADMINISTRADOR"))
        self.producto = Producto.objects.create(
            empresa=self.empresa, nombre="Prod", sku="CONC-1",
            precio=5000, stock=1, activo=True)
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, nombre="Cli",
            tipo_documento="CC", numero_documento="9022222222")

    def _vender(self, resultados, indice):
        api = APIClient()
        api.force_authenticate(self.user)
        resp = api.post("/api/ventas/pos/", {
            "cliente": str(self.cliente.id),
            "detalles": [{"producto": str(self.producto.id), "cantidad": 1}],
            "metodo_pago": "efectivo",
            "descuento": "0",
        }, format="json")
        resultados[indice] = resp.status_code

    def test_dos_ventas_simultaneas_no_sobrevenden(self):
        resultados = {}
        hilos = [
            threading.Thread(target=self._vender, args=(resultados, 0)),
            threading.Thread(target=self._vender, args=(resultados, 1)),
        ]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        codigos = sorted(resultados.values())
        # Con stock=1 y 2 ventas de 1 ud: solo una puede completarse (201);
        # la otra debe dar stock insuficiente (400).
        self.assertEqual(codigos[0], 201)
        self.assertEqual(codigos[1], 400)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 0)
        self.assertEqual(Venta.objects.count(), 1)


# -------------------- Carreras: checkout ----------------------------------

class ConcurrenciaCheckout(TransactionTestCase):
    """Dos checkouts simultaneos del mismo comprador: un solo carrito victima."""

    def setUp(self):
        call_command("seed_roles")
        self.vendedor = Empresa.objects.create(nombre="Vend", nit="900666001")
        self.producto = Producto.objects.create(
            empresa=self.vendedor, nombre="P", sku="CHK-1",
            precio=1000, stock=100, activo=True)
        self.comprador = User.objects.create_user(username="chk@test.co",
                                                  email="chk@test.co",
                                                  password="Clave12345")
        Perfil.objects.create(usuario=self.comprador, empresa=None,
                              rol=Rol.de_nombre("CLIENTE"))
        self.cliente = Cliente.objects.create(
            usuario=self.comprador, empresa=None, nombre="Comprador",
            tipo_documento="CC", numero_documento="9033333333")
        # Un solo item en el carrito compartido, antes de lanzar los hilos.
        self.carrito = Carrito.objects.create(usuario=self.comprador)
        CarritoItem.objects.create(carrito=self.carrito,
                                   producto=self.producto, cantidad=1)

    def _checkout(self, resultados, indice):
        api = APIClient()
        api.force_authenticate(self.comprador)
        resp = api.post("/api/tienda/checkout/",
                        {"metodo_pago": "tarjeta"}, format="json")
        resultados[indice] = resp.status_code

    def test_doble_checkout_se_serializa(self):
        resultados = {}
        hilos = [
            threading.Thread(target=self._checkout, args=(resultados, 0)),
            threading.Thread(target=self._checkout, args=(resultados, 1)),
        ]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        # Uno gana (201); el otro con carrito vacio da CARRITO_VACIO (400).
        self.assertEqual(sorted(resultados.values()), [201, 400])
        self.assertEqual(Venta.objects.filter(cliente=self.cliente).count(), 1)
