"""Fase 3: pruebas de aislamiento multiempresa.

Verifica que cada tenant (empresa) solo pueda leer, crear, actualizar y
eliminar SUS datos de negocio y nunca los de otra empresa. Se usan DOS
empresas (A y B) con personal propio y datos propios, y se comprueba:

- GET/POST: la empresa A no ve en listados ni revuelve datos de la empresa B;
  al crear, `empresa` se asigna desde request.user.perfil.empresa.
- PATCH/PUT/DELETE: operar sobre un recurso de la empresa ajena da 404.
- Roles del sistema (ADMINISTRADOR/EMPLEADO/CLIENTE): son globales y de solo
  lectura -> ningun admin puede editar/eliminar sus permisos.
- Regresiones de las vulnerabilidades corregidas: lectura del movimiento de
  inventario y resolucion de cupones acotada al carrito/empresa.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from cuentas.models import Perfil, Rol

from .models import (Carrito, CarritoItem, Categoria, Cliente, Cupon, Empresa,
                     FacturaElectronica, MovimientoInventario, Notificacion,
                     Producto, Venta)


class BaseAislamientoTest(TestCase):
    """Dos empresas con admin, empleado y datos propios."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")

        cls.empresa_a = Empresa.objects.create(nombre="Tienda A", nit="900300001")
        cls.empresa_b = Empresa.objects.create(nombre="Tienda B", nit="900300002")

        cls.admin_a = cls._cuenta("admina@test.co", cls.empresa_a, "ADMINISTRADOR")
        cls.admin_b = cls._cuenta("adminb@test.co", cls.empresa_b, "ADMINISTRADOR")
        cls.emp_a = cls._cuenta("empa@test.co", cls.empresa_a, "EMPLEADO")
        cls.emp_b = cls._cuenta("empb@test.co", cls.empresa_b, "EMPLEADO")

        cls.categoria_a = Categoria.objects.create(empresa=cls.empresa_a,
                                                   nombre="Categoria A")
        cls.producto_a = Producto.objects.create(
            empresa=cls.empresa_a, nombre="Producto A", sku="SKU-A1",
            precio=10000, stock=50, stock_minimo=5)
        cls.producto_b = Producto.objects.create(
            empresa=cls.empresa_b, nombre="Producto B", sku="SKU-B1",
            precio=20000, stock=60, stock_minimo=6)

        cls.cliente_a = Cliente.objects.create(
            empresa=cls.empresa_a, nombre="Cliente A",
            tipo_documento="CC", numero_documento="3011111111")
        cls.cliente_b = Cliente.objects.create(
            empresa=cls.empresa_b, nombre="Cliente B",
            tipo_documento="CC", numero_documento="3022222222")

        cls.venta_a = Venta.objects.create(
            empresa=cls.empresa_a, cliente=cls.cliente_a,
            vendedor=cls.admin_a, total=10000, estado="completada")
        cls.venta_b = Venta.objects.create(
            empresa=cls.empresa_b, cliente=cls.cliente_b,
            vendedor=cls.admin_b, total=20000, estado="completada")

    @classmethod
    def _cuenta(cls, email, empresa, rol):
        user = User.objects.create_user(username=email, email=email,
                                        password="Clave12345",
                                        first_name=email.split("@")[0])
        Perfil.objects.create(usuario=user, empresa=empresa,
                              rol=Rol.de_nombre(rol))
        return user

    @classmethod
    def api_como(cls, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    @classmethod
    def api_a(cls):
        return cls.api_como(cls.admin_a)

    @classmethod
    def api_b(cls):
        return cls.api_como(cls.admin_b)


# ============================ Productos ============================

class AislamientoProductosTest(BaseAislamientoTest):
    def test_listado_solo_muestra_productos_de_mi_empresa(self):
        api = self.api_a()
        resultado = api.get("/api/productos/").json()
        ids = {p["id"] for p in resultado["resultados"]}
        self.assertIn(str(self.producto_a.id), ids)
        self.assertNotIn(str(self.producto_b.id), ids)

    def test_detalle_de_producto_ajeno_devuelve_404(self):
        self.assertEqual(self.api_a().get(
            f"/api/productos/{self.producto_b.id}/").status_code, 404)

    def test_crear_producto_queda_en_mi_empresa(self):
        api = self.api_a()
        respuesta = api.post("/api/productos/", {
            "nombre": "Nuevo A", "sku": "SKU-A2", "precio": 9999,
            "stock": 10, "stock_minimo": 2, "categoria": str(self.categoria_a.id),
        }, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        creado = Producto.objects.get(pk=respuesta.json()["id"])
        self.assertEqual(creado.empresa_id, self.empresa_a.id)

    def test_patch_de_producto_ajeno_devuelve_404(self):
        self.assertEqual(self.api_a().patch(
            f"/api/productos/{self.producto_b.id}/",
            {"nombre": "Hackeado"}, format="json").status_code, 404)

    def test_delete_de_producto_ajeno_devuelve_404(self):
        self.assertEqual(self.api_a().delete(
            f"/api/productos/{self.producto_b.id}/").status_code, 404)
        self.producto_b.refresh_from_db()
        self.assertIsNone(self.producto_b.deleted_at)


# ============================ Clientes ============================

class AislamientoClientesTest(BaseAislamientoTest):
    def test_listado_solo_muestra_clientes_de_mi_empresa(self):
        resultado = self.api_a().get("/api/clientes/").json()
        ids = {c["id"] for c in resultado["resultados"]}
        self.assertIn(str(self.cliente_a.id), ids)
        self.assertNotIn(str(self.cliente_b.id), ids)

    def test_detalle_cliente_ajeno_devuelve_404(self):
        self.assertEqual(self.api_a().get(
            f"/api/clientes/{self.cliente_b.id}/").status_code, 404)

    def test_patch_cliente_ajeno_devuelve_404(self):
        self.assertEqual(self.api_a().patch(
            f"/api/clientes/{self.cliente_b.id}/",
            {"nombre": "Falso"}, format="json").status_code, 404)

    def test_delete_cliente_ajeno_devuelve_404(self):
        self.assertEqual(self.api_a().delete(
            f"/api/clientes/{self.cliente_b.id}/").status_code, 404)
        self.cliente_b.refresh_from_db()
        self.assertIsNone(self.cliente_b.deleted_at)


# ============================ Ventas ============================

class AislamientoVentasTest(BaseAislamientoTest):
    def test_listado_ventas_solo_de_mi_empresa(self):
        resultado = self.api_a().get("/api/ventas/").json()
        ids = {v["id"] for v in resultado["resultados"]}
        self.assertIn(str(self.venta_a.id), ids)
        self.assertNotIn(str(self.venta_b.id), ids)

    def test_detalle_venta_ajena_devuelve_404(self):
        self.assertEqual(self.api_a().get(
            f"/api/ventas/{self.venta_b.id}/").status_code, 404)

    def test_anular_venta_ajena_devuelve_404(self):
        respuesta = self.api_a().post(
            f"/api/ventas/{self.venta_b.id}/anular/",
            {"motivo": "prueba"}, format="json")
        self.assertEqual(respuesta.status_code, 404)
        self.venta_b.refresh_from_db()
        self.assertEqual(self.venta_b.estado, "completada")

    def test_pos_no_acepta_cliente_de_otra_empresa(self):
        respuesta = self.api_a().post("/api/ventas/pos/", {
            "cliente": str(self.cliente_b.id),   # cliente de empresa B
            "metodo_pago": "efectivo",
            "detalles": [{"producto": str(self.producto_a.id), "cantidad": 1}],
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "CLIENTE_NO_ENCONTRADO")

    def test_pos_no_acepta_producto_de_otra_empresa(self):
        respuesta = self.api_a().post("/api/ventas/pos/", {
            "cliente": str(self.cliente_a.id),
            "metodo_pago": "efectivo",
            "detalles": [{"producto": str(self.producto_b.id), "cantidad": 1}],
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "STOCK_INSUFICIENTE")
        # El producto ajeno no se resuelve -> se reporta como no encontrado
        producto = respuesta.json()["productos"][0]
        self.assertEqual(producto["producto"], str(self.producto_b.id))
        self.assertEqual(producto["producto_nombre"], "No encontrado")


# ==================== Movimiento de inventario (regresion) ====================

class AislamientoInventarioTest(BaseAislamientoTest):
    def test_ajuste_devuelve_movimiento_de_la_misma_empresa(self):
        # Movimiento previo de OTRA empresa; si la respuesta leyera
        # `MovimientoInventario.objects.latest()` sin filtrar, devolveria
        # este movimiento ajeno (era la fuga corregida).
        MovimientoInventario.objects.create(
            producto=self.producto_b, usuario=self.admin_b, tipo="entrada",
            cantidad=7, motivo="movimiento ajeno")

        respuesta = self.api_a().post(
            f"/api/inventario/{self.producto_a.id}/ajustar/",
            {"producto": str(self.producto_a.id), "cantidad": 3,
             "tipo": "entrada", "motivo": "revision"}, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        movimiento = respuesta.json()
        self.assertEqual(movimiento["producto_nombre"], "Producto A")
        self.assertEqual(movimiento["producto_sku"], "SKU-A1")
        self.assertNotEqual(movimiento["producto_nombre"], "Producto B")


# ============================ Roles del sistema ============================

class RolesSistemaSoloLecturaTest(BaseAislamientoTest):
    """Fase 3: los roles del sistema son globales y de solo lectura.

    Ningun administrador puede renombrarlos, cambiarles descripcion ni
    modificar sus permisos (eso alteraria la autorizacion de TODAS las
    empresas), ni eliminarlos.
    """

    def test_admin_no_puede_editar_permisos_de_rol_del_sistema(self):
        rol_admin = Rol.objects.get(nombre="ADMINISTRADOR")
        respuesta = self.api_a().patch(
            f"/api/seguridad/roles/{rol_admin.id}/",
            {"permisos": []}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "ROL_SISTEMA_LECTURA_ONLY")
        # Los permisos no cambiaron
        self.assertTrue(rol_admin.perfiles.filter(
            usuario=self.admin_a).exists())
        self.assertTrue(Perfil.objects.get(usuario=self.admin_a)
                        .tiene_permiso("usuarios.gestionar"))

    def test_admin_no_puede_editar_descripcion_de_rol_del_sistema(self):
        rol = Rol.objects.get(nombre="EMPLEADO")
        respuesta = self.api_a().patch(
            f"/api/seguridad/roles/{rol.id}/",
            {"descripcion": "modificada"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "ROL_SISTEMA_LECTURA_ONLY")

    def test_admin_no_puede_eliminar_rol_del_sistema(self):
        for nombre in ("ADMINISTRADOR", "EMPLEADO", "CLIENTE"):
            rol = Rol.objects.get(nombre=nombre)
            respuesta = self.api_a().delete(
                f"/api/seguridad/roles/{rol.id}/")
            self.assertEqual(respuesta.status_code, 400)
            self.assertEqual(respuesta.json()["codigo"],
                             "ROL_SISTEMA_LECTURA_ONLY")
            self.assertTrue(Rol.objects.filter(pk=rol.pk).exists())

    def test_roles_sistema_siguen_compartidos_y_asignables(self):
        # Sigue siendo un rol global: lo ve y lo asigna cualquier empresa.
        lista = self.api_b().get("/api/seguridad/roles/").json()
        nombres = [r["nombre"] for r in lista["resultados"]]
        for nombre in ("ADMINISTRADOR", "EMPLEADO", "CLIENTE"):
            self.assertIn(nombre, nombres)


# ============================ Cupones (regresion) ============================
class AislamientoCuponTest(BaseAislamientoTest):
    """El cupon de una empresa solo es validable cuando dicha empresa esta en
    el carrito del comprador (alcance derivado de datos de servidor)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ahora = timezone.now()
        cls.cupon_a = Cupon.objects.create(
            empresa=cls.empresa_a, codigo="CUPON-A", porcentaje="10",
            fecha_inicio=cls.ahora - timedelta(days=1),
            fecha_fin=cls.ahora + timedelta(days=1))
        cls.cupon_b = Cupon.objects.create(
            empresa=cls.empresa_b, codigo="CUPON-B", porcentaje="20",
            fecha_inicio=cls.ahora - timedelta(days=1),
            fecha_fin=cls.ahora + timedelta(days=1))

        cls.comprador = User.objects.create_user(
            username="comprador@app.co", email="comprador@app.co",
            password="Clave12345")
        Perfil.objects.create(usuario=cls.comprador, empresa=None,
                              rol=Rol.de_nombre("CLIENTE"))
        cls.api_buyer = APIClient()
        cls.api_buyer.force_authenticate(cls.comprador)

    def test_no_puede_validar_un_cupon_de_un_tenant_sin_carrito(self):
        # Carrito con un producto de la empresa A: solo esta vigente/valido
        # el cupon de A. El cupon de B (tenant ajeno) no debe resolverse.
        carrito = Carrito.objects.create(usuario=self.comprador, empresa=None)
        CarritoItem.objects.create(carrito=carrito, producto=self.producto_a,
                                   cantidad=1)

        resp = self.api_buyer.post("/api/tienda/cupones/validar/",
                                   {"codigo": "CUPON-B"}, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["codigo"], "NO_ENCONTRADO")

        resp = self.api_buyer.post("/api/tienda/cupones/validar/",
                                   {"codigo": "CUPON-A"}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_cupon_validation_requiere_autenticacion(self):
        resp = APIClient().post("/api/tienda/cupones/validar/",
                                {"codigo": "CUPON-A"}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_crear_cupon_rechaza_porcentaje_fuera_de_rango(self):
        api = self.api_a()
        resp = api.post("/api/tienda/cupones/", {
            "codigo": "MAL-500", "porcentaje": "500",
            "fecha_inicio": self.ahora.isoformat(),
            "fecha_fin": (self.ahora + timedelta(days=1)).isoformat(),
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("porcentaje", str(resp.json()["errores"]).lower())
        self.assertFalse(Cupon.objects.filter(codigo="MAL-500").exists())

        resp = api.post("/api/tienda/cupones/", {
            "codigo": "MAL-NEG", "porcentaje": "-10",
            "fecha_inicio": self.ahora.isoformat(),
            "fecha_fin": (self.ahora + timedelta(days=1)).isoformat(),
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_crear_cupon_rechaza_fecha_fin_anterior_a_inicio(self):
        api = self.api_a()
        resp = api.post("/api/tienda/cupones/", {
            "codigo": "FECHAS-MAL", "porcentaje": "10",
            "fecha_inicio": self.ahora.isoformat(),
            "fecha_fin": (self.ahora - timedelta(days=1)).isoformat(),
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("fecha_fin", resp.json()["errores"])
        self.assertFalse(Cupon.objects.filter(codigo="FECHAS-MAL").exists())


# ======================== Reportes (alcance por empresa) =====================

class AislamientoReportesTest(BaseAislamientoTest):
    def test_reporte_ignora_datos_de_otra_empresa(self):
        def reporte_a():
            return self.api_a().get("/api/reportes/vista/?tipo=ventas_diarias")

        base = reporte_a()
        self.assertEqual(base.status_code, 200)

        # Venta ajena de la empresa B (mismo dia), de importe alto y unico.
        Venta.objects.create(
            empresa=self.empresa_b, cliente=self.cliente_b,
            vendedor=self.admin_b, total=999999, estado="completada")

        despues = reporte_a()
        self.assertEqual(despues.status_code, 200)
        # El reporte de A no cambia al aparecer una venta de B: no hay fuga.
        self.assertEqual(base.data, despues.data)


# ======================== Notificaciones (alcance por empresa) ================

class AislamientoNotificacionesTest(BaseAislamientoTest):
    def test_listado_solo_muestra_notificaciones_de_mi_empresa(self):
        Notificacion.objects.create(empresa=self.empresa_b, usuario=self.admin_b,
                                    tipo="stock", estado="nueva",
                                    mensaje="Aviso de la empresa B")
        resultado = self.api_a().get("/api/notificaciones/")
        self.assertEqual(resultado.status_code, 200)
        mensajes = [n["mensaje"] for n in resultado.json()["resultados"]]
        self.assertNotIn("Aviso de la empresa B", mensajes)

    def test_no_puede_marcar_notificacion_ajena(self):
        aviso = Notificacion.objects.create(empresa=self.empresa_b,
                                            usuario=self.admin_b, tipo="stock",
                                            estado="nueva", mensaje="Aviso de B")
        resp = self.api_a().patch(
            f"/api/notificaciones/{aviso.id}/", {"estado": "revisada"},
            format="json")
        self.assertEqual(resp.status_code, 404)
        aviso.refresh_from_db()
        self.assertEqual(aviso.estado, "nueva")


# ======================== Facturas (alcance por empresa) =====================

class AislamientoFacturasTest(BaseAislamientoTest):
    def test_listado_solo_muestra_facturas_de_mi_empresa(self):
        venta_ajena = Venta.objects.create(
            empresa=self.empresa_b, cliente=self.cliente_b,
            vendedor=self.admin_b, total=50000, estado="completada")
        FacturaElectronica.objects.create(venta=venta_ajena,
                                          numero=f"FE-{venta_ajena.numero_factura}")

        resultado = self.api_a().get("/api/facturacion/")
        self.assertEqual(resultado.status_code, 200)
        numeros = [f["numero"] for f in resultado.json()["resultados"]]
        self.assertNotIn(f"FE-{venta_ajena.numero_factura}", numeros)

    def test_detalle_factura_ajena_devuelve_404(self):
        venta_ajena = Venta.objects.create(
            empresa=self.empresa_b, cliente=self.cliente_b,
            vendedor=self.admin_b, total=50000, estado="completada")
        factura = FacturaElectronica.objects.create(
            venta=venta_ajena, numero=f"FE-{venta_ajena.numero_factura}")

        resp = self.api_a().get(f"/api/facturacion/{factura.id}/")
        self.assertEqual(resp.status_code, 404)
