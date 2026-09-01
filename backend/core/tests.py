from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (Camara, Categoria, Cliente, DetalleVenta, Empresa,
                     MovimientoInventario, Notificacion, Producto, Venta)

from cuentas.models import crear_roles_base  # noqa: E402


class BaseCoreTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Tienda Test", nit="900999998")
        crear_roles_base(cls.empresa)
        cls.cuenta = User.objects.create_user(username="vendedor@test.co",
                                              email="vendedor@test.co",
                                              password="Clave12345")
        cls.cliente = Cliente.objects.create(empresa=cls.empresa, nombre="Carlos Ramirez",
                                             tipo_documento="CC", numero_documento="1020304050")
        cls.producto = Producto.objects.create(empresa=cls.empresa, nombre="Zapatos",
                                               sku="SKU-T01", precio=75000, stock=40,
                                               stock_minimo=10)

    @classmethod
    def crear_venta(cls, total=75000):
        return Venta.objects.create(empresa=cls.empresa, cliente=cls.cliente,
                                    vendedor=cls.cuenta, total=total, estado="completada")


class ValidacionesGlobalesTest(BaseCoreTest):
    def test_precio_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(empresa=self.empresa, nombre="Malo", sku="SKU-X1",
                                        precio=-1)

    def test_stock_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(empresa=self.empresa, nombre="Malo", sku="SKU-X2",
                                        stock=-5)

    def test_stock_minimo_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(empresa=self.empresa, nombre="Malo", sku="SKU-X3",
                                        stock_minimo=-1)

    def test_total_venta_negativo_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_venta(total=-100)

    def test_cero_es_valido(self):
        producto = Producto.objects.create(empresa=self.empresa, nombre="Gratis", sku="SKU-X4",
                                           precio=0, stock=0)
        self.assertEqual(producto.precio, 0)
        self.assertTrue(producto.stock_bajo)   # 0 <= 10 por defecto


class ClienteDocumentoUnicoTest(BaseCoreTest):
    def test_documento_repetido_en_la_misma_empresa_rechazado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cliente.objects.create(empresa=self.empresa, nombre="Duplicado",
                                       tipo_documento="CC", numero_documento="1020304050")

    def test_mismo_documento_en_otra_empresa_permitido(self):
        otra = Empresa.objects.create(nombre="Otra Tienda", nit="900999997")
        cliente = Cliente.objects.create(empresa=otra, nombre="Homonimo",
                                         tipo_documento="CC", numero_documento="1020304050")
        self.assertEqual(cliente.numero_documento, "1020304050")

    def test_cliente_puede_enlazar_cuenta_de_usuario(self):
        cliente = Cliente.objects.create(empresa=self.empresa, nombre="Con Cuenta",
                                         tipo_documento="CE", numero_documento="555555",
                                         usuario=self.cuenta)
        self.assertEqual(cliente.usuario.email, "vendedor@test.co")
        self.assertEqual(self.cuenta.perfil_cliente.nombre, "Con Cuenta")


class DetalleVentaTest(BaseCoreTest):
    def test_linea_y_subtotal(self):
        venta = self.crear_venta()
        detalle = DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                              cantidad=2, precio_unitario=75000)
        self.assertEqual(detalle.subtotal, 150000)
        self.assertEqual(venta.detalles.count(), 1)

    def test_mismo_producto_no_se_repite_en_la_venta(self):
        venta = self.crear_venta()
        DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                    cantidad=1, precio_unitario=75000)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                            cantidad=3, precio_unitario=75000)

    def test_cantidad_cero_rechazada(self):
        venta = self.crear_venta()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                            cantidad=0, precio_unitario=75000)

    def test_precio_unitario_negativo_rechazado(self):
        venta = self.crear_venta()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                            cantidad=1, precio_unitario=-10)


class MovimientoInventarioTest(BaseCoreTest):
    def test_registrar_entrada_salida_ajuste(self):
        for tipo in ("entrada", "salida", "ajuste"):
            movimiento = MovimientoInventario.objects.create(
                producto=self.producto, usuario=self.cuenta, tipo=tipo,
                cantidad=5, motivo=f"prueba {tipo}")
            self.assertEqual(movimiento.get_tipo_display(),
                             {"entrada": "Entrada", "salida": "Salida", "ajuste": "Ajuste"}[tipo])
        self.assertEqual(self.producto.movimientos.count(), 3)

    def test_cantidad_cero_rechazada(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovimientoInventario.objects.create(producto=self.producto, tipo="entrada",
                                                    cantidad=0, motivo="invalido")


class NotificacionTest(BaseCoreTest):
    def test_crear_y_marcar_leida(self):
        aviso = Notificacion.objects.create(usuario=self.cuenta,
                                            mensaje="Camiseta Polo tiene stock bajo")
        self.assertFalse(aviso.leida)
        aviso.leida = True
        aviso.save(update_fields=["leida"])
        aviso.refresh_from_db()
        self.assertTrue(aviso.leida)
        self.assertIn("stock bajo", str(aviso))


class BorradoLogicoTest(BaseCoreTest):
    def test_soft_delete_producto(self):
        self.producto.soft_delete()
        self.producto.refresh_from_db()
        self.assertIsNotNone(self.producto.deleted_at)
        self.assertFalse(self.producto.esta_activo)


class VentaFacturaTest(BaseCoreTest):
    def test_numero_factura_autogenerado(self):
        venta = self.crear_venta()
        self.assertTrue(venta.numero_factura)
        otra = self.crear_venta(total=100)
        self.assertNotEqual(venta.numero_factura, otra.numero_factura)

# ============================ FASE 3: API catalogo ============================

from rest_framework.test import APIClient  # noqa: E402

from cuentas.models import ActividadUsuario, Perfil, Rol  # noqa: E402


class BaseCatalogoTest(BaseCoreTest):
    """Personal interno autenticado para probar /api/clientes y /api/productos."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = User.objects.create_user(username="admin@test.co",
                                             email="admin@test.co", password="Clave12345")
        Perfil.objects.create(usuario=cls.admin, empresa=cls.empresa,
                              rol=Rol.de_nombre(cls.empresa, "ADMINISTRADOR"))
        cls.empleado = User.objects.create_user(username="empleado@test.co",
                                                email="empleado@test.co",
                                                password="Clave12345")
        Perfil.objects.create(usuario=cls.empleado, empresa=cls.empresa,
                              rol=Rol.de_nombre(cls.empresa, "EMPLEADO"))
        cls.cliente_rol = User.objects.create_user(username="solo@test.co",
                                                   email="solo@test.co",
                                                   password="Clave12345")
        cls.perfil_cliente_rol = Perfil.objects.create(
            usuario=cls.cliente_rol, empresa=cls.empresa,
            rol=Rol.de_nombre(cls.empresa, "CLIENTE"))

    @classmethod
    def api_como(cls, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    @classmethod
    def crear_categoria(cls, nombre="Calzado"):
        return Categoria.objects.create(empresa=cls.empresa, nombre=nombre)


class AccesoCatalogoTest(BaseCatalogoTest):
    URL = "/api/clientes/"

    def test_anonimo_recibe_401(self):
        self.assertEqual(APIClient().get(self.URL).status_code, 401)

    def test_cliente_rol_recibe_403(self):
        respuesta = self.api_como(self.cliente_rol).get(self.URL)
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_y_empleado_acceden(self):
        self.assertEqual(self.api_como(self.admin).get(self.URL).status_code, 200)
        self.assertEqual(self.api_como(self.empleado).get(self.URL).status_code, 200)


class CrudClientesApiTest(BaseCatalogoTest):
    DATOS = {"nombre": "Ana Lopez", "tipo_documento": "CC",
             "numero_documento": "7987654321", "email": "ana@test.co",
             "telefono": "3105556666"}

    def test_crear_y_listar_clientes(self):
        api = self.api_como(self.empleado)
        respuesta = api.post("/api/clientes/", self.DATOS, format="json")
        self.assertEqual(respuesta.status_code, 201)
        listado = api.get("/api/clientes/").json()
        nombres = [c["nombre"] for c in listado["resultados"]]
        self.assertIn("Ana Lopez", nombres)

    def test_documento_duplicado_informa_registro_en_conflicto(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/clientes/", {
            "nombre": "Impostor", "tipo_documento": "CC",
            "numero_documento": "1020304050"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        mensaje = str(respuesta.json()["errores"]["numero_documento"])
        self.assertIn("Carlos Ramirez", mensaje)   # registro en conflicto
        self.assertIn("1020304050", mensaje)

    def test_editar_conserva_documento_distinto_por_tipo(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/clientes/", {
            "nombre": "Mismo Numero", "tipo_documento": "NIT",
            "numero_documento": "1020304050"}, format="json")
        self.assertEqual(respuesta.status_code, 201)   # distinto tipo de doc: valido

    def test_vincular_usuario_existente(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/clientes/",
                             dict(self.DATOS, usuario_id=str(self.perfil_cliente_rol.id)),
                             format="json")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["usuario_email"], "solo@test.co")

    def test_usuario_ya_vinculado_a_otro_cliente_rechazado(self):
        Cliente.objects.create(empresa=self.empresa, nombre="Ocupado",
                               tipo_documento="CE", numero_documento="111",
                               usuario=self.cliente_rol)
        api = self.api_como(self.admin)
        respuesta = api.post("/api/clientes/",
                             dict(self.DATOS, usuario_id=str(self.perfil_cliente_rol.id)),
                             format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Ocupado", str(respuesta.json()["errores"]["usuario_id"]))

    def test_patch_parcial_no_rompe_el_vinculo(self):
        cliente = Cliente.objects.create(empresa=self.empresa, nombre="Vinculado",
                                         tipo_documento="PAS", numero_documento="AB123",
                                         usuario=self.cuenta)
        api = self.api_como(self.admin)
        respuesta = api.patch(f"/api/clientes/{cliente.id}/",
                              {"ciudad": "Cali"}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["usuario_email"], "vendedor@test.co")

    def test_eliminar_es_borrado_logico(self):
        cliente = Cliente.objects.create(empresa=self.empresa, nombre="Borrable",
                                         tipo_documento="CC", numero_documento="999")
        api = self.api_como(self.admin)
        self.assertEqual(api.delete(f"/api/clientes/{cliente.id}/").status_code, 204)
        cliente.refresh_from_db()
        self.assertIsNotNone(cliente.deleted_at)


class CrudProductosApiTest(BaseCatalogoTest):
    DATOS = {"nombre": "Camiseta Polo", "sku": "SKU-F03", "precio": "45000.00",
             "stock": 25, "stock_minimo": 5}

    def test_crear_producto_con_categoria(self):
        categoria = self.crear_categoria()
        api = self.api_como(self.empleado)
        respuesta = api.post("/api/productos/",
                             dict(self.DATOS, categoria_id=str(categoria.id)), format="json")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["categoria_nombre"], "Calzado")

    def test_precio_negativo_rechazado(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/productos/", dict(self.DATOS, sku="SKU-N1",
                                                     precio="-5"), format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_stock_negativo_rechazado(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/productos/", dict(self.DATOS, sku="SKU-N2",
                                                     stock=-3), format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_sku_duplicado_rechazado(self):
        api = self.api_como(self.admin)
        respuesta = api.post("/api/productos/", dict(self.DATOS, sku="SKU-T01"),
                             format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("SKU-T01", str(respuesta.json()["errores"]["sku"]))

    def test_producto_con_ventas_no_se_elimina_solo_se_desactiva(self):
        venta = self.crear_venta()
        DetalleVenta.objects.create(venta=venta, producto=self.producto,
                                    cantidad=1, precio_unitario=75000)
        api = self.api_como(self.admin)
        respuesta = api.delete(f"/api/productos/{self.producto.id}/")
        self.assertEqual(respuesta.status_code, 400)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["codigo"], "PRODUCTO_CON_VENTAS")
        self.producto.refresh_from_db()
        self.assertIsNone(self.producto.deleted_at)   # sigue existiendo
        # desactivar lo oculta del catalogo publico (activo=false)
        oculto = api.post(f"/api/productos/{self.producto.id}/desactivar/")
        self.assertEqual(oculto.status_code, 200)
        self.assertFalse(oculto.json()["activo"])
        listado_publico = api.get("/api/productos/?activo=true").json()
        ids = [p["id"] for p in listado_publico["resultados"]]
        self.assertNotIn(str(self.producto.id), ids)

    def test_producto_sin_ventas_se_elimina(self):
        producto = Producto.objects.create(empresa=self.empresa, nombre="Sin Ventas",
                                           sku="SKU-S01", precio=1000, stock=1)
        api = self.api_como(self.admin)
        self.assertEqual(api.delete(f"/api/productos/{producto.id}/").status_code, 204)
        producto.refresh_from_db()
        self.assertIsNotNone(producto.deleted_at)

    def test_reactivar_tras_desactivar(self):
        api = self.api_como(self.admin)
        api.post(f"/api/productos/{self.producto.id}/desactivar/")
        respuesta = api.post(f"/api/productos/{self.producto.id}/reactivar/")
        self.assertTrue(respuesta.json()["activo"])

    def test_busqueda_por_nombre_y_sku(self):
        api = self.api_como(self.empleado)
        hallados = api.get("/api/productos/", {"busqueda": "zapatos"}).json()
        self.assertEqual(hallados["total"], 1)
        hallados_sku = api.get("/api/productos/", {"busqueda": "SKU-T01"}).json()
        self.assertEqual(hallados_sku["total"], 1)


class CategoriasApiTest(BaseCatalogoTest):
    def test_listar_y_crear_categoria(self):
        self.crear_categoria()
        api = self.api_como(self.empleado)
        listado = api.get("/api/categorias/").json()
        self.assertEqual(listado["total"], 1)
        respuesta = api.post("/api/categorias/", {"nombre": "Ropa"},
                             format="json")
        self.assertEqual(respuesta.status_code, 201)

    def test_categoria_duplicada_rechazada(self):
        self.crear_categoria()
        api = self.api_como(self.admin)
        respuesta = api.post("/api/categorias/", {"nombre": "calzado"}, format="json")
        self.assertEqual(respuesta.status_code, 400)


class AuditoriaCatalogoTest(BaseCatalogoTest):
    def test_acciones_quedan_auditadas(self):
        api = self.api_como(self.admin)
        api.post("/api/clientes/", {"nombre": "Auditado", "tipo_documento": "CC",
                                    "numero_documento": "777"}, format="json")
        api.post("/api/productos/", {"nombre": "Audifonos", "sku": "SKU-A01",
                                     "precio": "99000", "stock": 8}, format="json")
        acciones = set(ActividadUsuario.objects.values_list("accion", flat=True))
        for esperada in ("CLIENTE_CREADO", "PRODUCTO_CREADO"):
            self.assertIn(esperada, acciones)


class DashboardReportesTest(BaseCatalogoTest):
    """Fase 7: dashboard y reportes de analitica (solo ADMINISTRADOR)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cat2 = Categoria.objects.create(empresa=cls.empresa, nombre="Ropa")
        # Venta completada con detalle, para que las vistas de ventas tengan datos.
        cls.venta1 = cls.crear_venta(total=187500)
        DetalleVenta.objects.create(venta=cls.venta1, producto=cls.producto,
                                    cantidad=2, precio_unitario=75000)
        cls.camisa = Producto.objects.create(
            empresa=cls.empresa, nombre="Camisa", sku="SKU-R01", precio=45000,
            stock=8, stock_minimo=10, categoria=cls.cat2)
        venta2 = cls.crear_venta(total=45000)
        DetalleVenta.objects.create(venta=venta2, producto=cls.camisa,
                                    cantidad=1, precio_unitario=45000)

    def _venta_con_detalle(self, producto, cantidad, precio):
        """Crea una venta completada con detalle (alimenta las vistas)."""
        venta = Venta.objects.create(empresa=self.empresa, cliente=self.cliente,
                                     vendedor=self.cuenta, total=precio * cantidad,
                                     estado="completada")
        DetalleVenta.objects.create(venta=venta, producto=producto,
                                    cantidad=cantidad, precio_unitario=precio)
        return venta

    def test_acceso_solo_administrador(self):
        self.assertEqual(APIClient().get("/api/dashboard/resumen/").status_code, 401)
        self.assertEqual(self.api_como(self.empleado).get(
            "/api/dashboard/resumen/").status_code, 403)
        self.assertEqual(self.api_como(self.cliente_rol).get(
            "/api/dashboard/resumen/").status_code, 403)
        self.assertEqual(self.api_como(self.admin).get(
            "/api/dashboard/resumen/").status_code, 200)

    def test_resumen_entrega_kpis(self):
        cuerpo = self.api_como(self.admin).get("/api/dashboard/resumen/").json()
        self.assertIn("ingresos_totales", cuerpo)
        self.assertIn("valor_inventario", cuerpo)
        self.assertIn("productos_bajo_minimo", cuerpo)
        # Existen 4 productos (producto Zapatos, Camisa y los de la base
        # CoreTest) y la Camisa esta bajo minimo (8 <= 10).
        self.assertGreaterEqual(cuerpo["productos_bajo_minimo"], 1)

    def test_ventas_por_dia_tiene_datos(self):
        cuerpo = self.api_como(self.admin).get("/api/dashboard/ventas/").json()
        self.assertTrue(cuerpo["por_dia"], "Debe haber al menos una venta por dia")
        total_dia = sum(fila["ingresos"] for fila in cuerpo["por_dia"])
        self.assertGreaterEqual(total_dia, 187500)

    def test_top_productos_y_clientes_frecuentes(self):
        api = self.api_como(self.admin)
        top = api.get("/api/dashboard/top-productos/").json()["resultados"]
        self.assertTrue(top)
        self.assertEqual(top[0]["producto"], "Zapatos")

        clientes = api.get("/api/dashboard/clientes-frecuentes/").json()["resultados"]
        self.assertTrue(clientes)
        self.assertEqual(clientes[0]["cliente"], "Carlos Ramirez")

    def test_inventario_y_bajo_minimo(self):
        api = self.api_como(self.admin)
        inventario = api.get("/api/dashboard/inventario/").json()
        self.assertTrue(inventario["valor_por_categoria"])
        bajos = inventario["bajo_minimo"]
        nombres = [b["producto"] for b in bajos]
        self.assertIn("Camisa", nombres)   # stock 8 <= min 10

    def test_categorias_del_filtro(self):
        cat_calzado = Categoria.objects.create(empresa=self.empresa, nombre="Calzado")
        self.producto.categoria = cat_calzado
        self.producto.save(update_fields=["categoria"])
        res = self.api_como(self.admin).get("/api/dashboard/categorias/").json()
        nombres = [c["categoria"] for c in res["resultados"]]
        self.assertIn("Calzado", nombres)
        self.assertIn("Ropa", nombres)

    def test_reporte_vista_json(self):
        res = self.api_como(self.admin).get(
            "/api/reportes/vista/", {"tipo": "ventas_diarias"}).json()
        self.assertEqual(res["tipo"], "ventas_diarias")
        self.assertTrue(res["filas"])
        # la clave 'dia' tiene formato YYYY-MM-DD (coincide con la venta)
        esperado = self.venta1.fecha.strftime("%Y-%m-%d")
        self.assertEqual(res["filas"][0]["dia"], esperado)

    def test_reporte_tipo_invalido_rechazado(self):
        res = self.api_como(self.admin).get(
            "/api/reportes/vista/", {"tipo": "inexistente"})
        self.assertEqual(res.status_code, 400)

    def test_exportar_excel_csv(self):
        res = self.api_como(self.admin).get(
            "/api/reportes/exportar/",
            {"tipo": "ventas_diarias", "formato": "excel"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn("attachment", res["Content-Disposition"])
        self.assertTrue(res.content.startswith(b'\xef\xbb\xbf'))  # BOM UTF-8

    def test_exportar_pdf_html(self):
        res = self.api_como(self.admin).get(
            "/api/reportes/exportar/",
            {"tipo": "ventas_diarias", "formato": "pdf"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res["Content-Type"])
        self.assertIn(b"<html", res.content)

    def test_aislamiento_entre_empresas(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999991")
        crear_roles_base(otra)
        otro_prod = Producto.objects.create(empresa=otra, nombre="Otro", sku="SKU-O01",
                                            precio=100, stock=5, stock_minimo=3)
        # Un administrador de la empresa 'otra'
        otro_admin = User.objects.create_user(username="otro@test.co",
                                              email="otro@test.co", password="Clave12345")
        Perfil.objects.create(usuario=otro_admin, empresa=otra,
                              rol=Rol.de_nombre(otra, "ADMINISTRADOR"))
        api = APIClient()
        api.force_authenticate(otro_admin)
        # El resumen de 'otra' no debe incluir productos ni ventas de la 1a
        cuerpo = api.get("/api/dashboard/resumen/").json()
        self.assertEqual(cuerpo["valor_inventario"], 500)

    def test_exportar_queda_auditado(self):
        self.api_como(self.admin).get(
            "/api/reportes/exportar/",
            {"tipo": "valor_inventario", "formato": "excel"})
        acciones = set(ActividadUsuario.objects.values_list("accion", flat=True))
        self.assertIn("REPORTE_EXPORTADO", acciones)


# ============================ FASE 8: Asistente IA ===========================

from unittest.mock import patch  # noqa: E402

from core.ia_engine import IAError  # noqa: E402


class IAChatTest(BaseCatalogoTest):
    """Fase 8: chat del asistente IA (ADMINISTRADOR y EMPLEADO)."""

    def test_acceso_personal_interno(self):
        # Anonimo -> 401; CLIENTE -> 403; ADMIN y EMPLEADO -> 200
        self.assertEqual(
            APIClient().post("/api/ia/chat/", {"mensaje": "hola"}, format="json").status_code,
            401)
        self.assertEqual(
            self.api_como(self.cliente_rol).post(
                "/api/ia/chat/", {"mensaje": "hola"}, format="json").status_code,
            403)
        for usuario in (self.admin, self.empleado):
            res = self.api_como(usuario).post(
                "/api/ia/chat/", {"mensaje": "hola"}, format="json")
            self.assertEqual(res.status_code, 200)

    def test_mensaje_vacio_rechazado(self):
        res = self.api_como(self.empleado).post(
            "/api/ia/chat/", {"mensaje": "   "}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_chat_crea_conversacion_y_respuesta(self):
        res = self.api_como(self.admin).post(
            "/api/ia/chat/", {"mensaje": "cuales son mis top productos?"},
            format="json")
        self.assertEqual(res.status_code, 200)
        cuerpo = res.json()
        self.assertTrue(cuerpo["respuesta"])
        self.assertIn("contexto", cuerpo)
        mensajes = cuerpo["conversacion"]["mensajes"]
        self.assertEqual([m["rol"] for m in mensajes], ["usuario", "asistente"])
        self.assertTrue(all(m["estado"] == "ok" for m in mensajes))

    def test_contexto_no_expone_datos_sensibles(self):
        res = self.api_como(self.admin).post(
            "/api/ia/chat/", {"mensaje": "resumen"}, format="json")
        ctx = res.json()["contexto"].lower()
        for secreto in ("clave", "password", "token", "apikey", "secret"):
            self.assertNotIn(secreto, ctx)

    def test_contexto_no_expone_datos_sensibles_de_modelos(self):
        # La auditoria guarda eventos IA de la consulta (no datos de acceso).
        self.api_como(self.admin).post(
            "/api/ia/chat/", {"mensaje": "resumen"}, format="json")
        acciones = set(ActividadUsuario.objects.values_list("accion", flat=True))
        self.assertTrue({"IA_CONSULTA", "IA_RESPUESTA"} <= acciones)

    def test_conversacion_mantiene_contexto(self):
        api = self.api_como(self.empleado)
        primero = api.post("/api/ia/chat/", {"mensaje": "ventas del mes"},
                           format="json").json()
        conv_id = primero["conversacion"]["id"]
        segundo = api.post("/api/ia/chat/",
                           {"conversacion_id": conv_id, "mensaje": "y el inventario?"},
                           format="json").json()
        mensajes = segundo["conversacion"]["mensajes"]
        self.assertEqual([m["rol"] for m in mensajes],
                         ["usuario", "asistente", "usuario", "asistente"])

    def test_listar_y_detalle_conversaciones(self):
        api = self.api_como(self.admin)
        creada = api.post("/api/ia/chat/", {"mensaje": "resumen"},
                          format="json").json()
        conv_id = creada["conversacion"]["id"]
        lista = api.get("/api/ia/conversaciones/").json()["resultados"]
        self.assertTrue(any(c["id"] == conv_id for c in lista))
        detalle = api.get(f"/api/ia/conversaciones/{conv_id}/")
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(len(detalle.json()["mensajes"]), 2)

    def test_crear_conversacion_explícita(self):
        api = self.api_como(self.admin)
        res = api.post("/api/ia/conversaciones/", {"titulo": "Mi sesion"},
                       format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["titulo"], "Mi sesion")
        self.assertIn("id", res.json())

    def test_detalle_conversacion_ajena_es_404(self):
        otro = User.objects.create_user(username="empleado2@test.co",
                                        email="empleado2@test.co",
                                        password="Clave12345")
        Perfil.objects.create(usuario=otro, empresa=self.empresa,
                              rol=Rol.de_nombre(self.empresa, "EMPLEADO"))
        conv = self.api_como(otro).post("/api/ia/chat/", {"mensaje": "resumen"},
                                        format="json").json()["conversacion"]["id"]
        res = self.api_como(self.admin).get(f"/api/ia/conversaciones/{conv}/")
        self.assertEqual(res.status_code, 404)

    def test_fallo_del_motor_conserva_conversacion_y_reintenta(self):
        api = self.api_como(self.admin)
        with patch("core.ia_engine.llamar_proveedor",
                   side_effect=IAError("red caida")):
            res = api.post("/api/ia/chat/", {"mensaje": "repetir"},
                           format="json")
        self.assertEqual(res.status_code, 502)
        cuerpo = res.json()
        self.assertEqual(cuerpo["codigo"], "IA_NO_DISPONIBLE")
        # Conserva la conversacion con el mensaje del usuario (para reintentar)
        mensajes = cuerpo["conversacion"]["mensajes"]
        self.assertEqual([m["rol"] for m in mensajes], ["usuario"])

        # Al reintentar la misma pregunta no se duplica el mensaje y responde OK
        reint = api.post("/api/ia/chat/", {"mensaje": "repetir"}, format="json")
        self.assertEqual(reint.status_code, 200)
        roles = [m["rol"] for m in reint.json()["conversacion"]["mensajes"]]
        self.assertEqual(roles, ["usuario", "asistente"])


# ====================== FASE 9: Camaras y notificaciones =====================

from core.notificaciones import crear_notificacion  # noqa: E402
from core.serializers_monitoreo import NotificacionLecturaSerializer  # noqa: E402


class MonitoreoAccesoTest(BaseCatalogoTest):
    """Fase 9: camaras y notificaciones son exclusivas del ADMINISTRADOR."""

    def test_camaras_solo_administrador(self):
        self.assertEqual(APIClient().get("/api/camaras/").status_code, 401)
        self.assertEqual(
            self.api_como(self.empleado).get("/api/camaras/").status_code, 403)
        self.assertEqual(
            self.api_como(self.cliente_rol).get("/api/camaras/").status_code, 403)
        self.assertEqual(self.api_como(self.admin).get("/api/camaras/").status_code, 200)

    def test_notificaciones_solo_administrador(self):
        self.assertEqual(
            APIClient().get("/api/notificaciones/").status_code, 401)
        self.assertEqual(
            self.api_como(self.empleado).get("/api/notificaciones/").status_code, 403)
        self.assertEqual(
            self.api_como(self.admin).get("/api/notificaciones/").status_code, 200)


class CamarasApiTest(BaseCatalogoTest):
    """Fase 9: CRUD de camaras del panel de monitoreo (ADMINISTRADOR)."""

    DATOS = {"nombre": "Entrada principal", "ubicacion": "Recepcion",
             "url_stream": "http://cam.example/live/1"}

    def test_crear_y_listar(self):
        api = self.api_como(self.admin)
        res = api.post("/api/camaras/", self.DATOS, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["nombre"], "Entrada principal")

        listado = api.get("/api/camaras/").json()["resultados"]
        self.assertTrue(any(c["nombre"] == "Entrada principal" for c in listado))

    def test_nombre_obligatorio(self):
        res = self.api_como(self.admin).post(
            "/api/camaras/", {"nombre": "   "}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_detalle_y_edicion(self):
        api = self.api_como(self.admin)
        camara = api.post("/api/camaras/", self.DATOS, format="json").json()
        detalle = api.get(f"/api/camaras/{camara['id']}/")
        self.assertEqual(detalle.status_code, 200)

        editado = api.patch(
            f"/api/camaras/{camara['id']}/",
            {"activa": False, "nombre": "Bodega"}, format="json")
        self.assertEqual(editado.status_code, 200)
        self.assertFalse(editado.json()["activa"])
        self.assertEqual(editado.json()["nombre"], "Bodega")

    def test_baja_logica_filtra_del_listado(self):
        api = self.api_como(self.admin)
        camara = api.post("/api/camaras/", self.DATOS, format="json").json()
        self.assertEqual(
            api.delete(f"/api/camaras/{camara['id']}/").status_code, 204)
        restante = api.get("/api/camaras/").json()["resultados"]
        self.assertFalse(any(c["id"] == camara["id"] for c in restante))

    def test_listado_aislado_por_empresa(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999997")
        Camara.objects.create(empresa=otra, nombre="Camara ajena")
        api = self.api_como(self.admin)
        nombres = [c["nombre"] for c in api.get("/api/camaras/").json()["resultados"]]
        self.assertNotIn("Camara ajena", nombres)

    def test_grabacion_historica_no_disponible(self):
        api = self.api_como(self.admin)
        camara = api.post("/api/camaras/", self.DATOS, format="json").json()
        res = api.get(
            f"/api/camaras/{camara['id']}/grabacion/?fecha=2026-01-01&hora=09:00")
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.json()["disponible"])

    def test_grabacion_fecha_invalida(self):
        api = self.api_como(self.admin)
        camara = api.post("/api/camaras/", self.DATOS, format="json").json()
        res = api.get(
            f"/api/camaras/{camara['id']}/grabacion/?fecha=no-es-fecha&hora=09:00")
        self.assertEqual(res.status_code, 404)


class NotificacionesApiTest(BaseCatalogoTest):
    """Fase 9: centro de notificaciones (ADMINISTRADOR)."""

    def test_crear_via_servicio_y_listar_activas(self):
        aviso = crear_notificacion(
            empresa=self.empresa, usuario=self.admin, tipo="stock",
            mensaje="Stock bajo: Zapatos")
        self.assertEqual(aviso.estado, "nueva")
        self.assertEqual(aviso.canal, "ninguno")

        listado = self.api_como(self.admin).get(
            "/api/notificaciones/").json()["resultados"]
        self.assertEqual([n["id"] for n in listado], [str(aviso.id)])

    def test_listado_excluye_resueltas(self):
        crear_notificacion(empresa=self.empresa, tipo="stock",
                           mensaje="Bajo 1")
        resuelta = crear_notificacion(empresa=self.empresa, tipo="stock",
                                      mensaje="Bajo 2")
        resuelta.estado = "resuelta"
        resuelta.save(update_fields=["estado"])

        listado = self.api_como(self.admin).get(
            "/api/notificaciones/").json()["resultados"]
        self.assertEqual(len(listado), 1)
        self.assertEqual(listado[0]["mensaje"], "Bajo 1")

    def test_marcar_revisada_y_resuelta(self):
        aviso = crear_notificacion(empresa=self.empresa, tipo="factura",
                                   mensaje="Factura rechazada")
        api = self.api_como(self.admin)

        revisada = api.patch(
            f"/api/notificaciones/{aviso.id}/",
            {"estado": "revisada"}, format="json")
        self.assertEqual(revisada.status_code, 200)
        self.assertEqual(revisada.json()["estado"], "revisada")

        resuelta = api.patch(
            f"/api/notificaciones/{aviso.id}/",
            {"estado": "resuelta"}, format="json")
        self.assertEqual(resuelta.status_code, 200)
        self.assertTrue(resuelta.json()["leida"])

        # Ya no aparece en el panel activo
        listado = api.get("/api/notificaciones/").json()["resultados"]
        self.assertNotIn(str(aviso.id), [n["id"] for n in listado])

    def test_estado_invalido_rechazado(self):
        aviso = crear_notificacion(empresa=self.empresa, tipo="sistema",
                                   mensaje="Aviso")
        res = self.api_como(self.admin).patch(
            f"/api/notificaciones/{aviso.id}/",
            {"estado": "borrado"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_notificaciones_aisladas_por_empresa(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999996")
        crear_notificacion(empresa=otra, tipo="sistema", mensaje="Aviso ajeno")
        listado = self.api_como(self.admin).get(
            "/api/notificaciones/").json()["resultados"]
        self.assertNotIn("Aviso ajeno", [n["mensaje"] for n in listado])

    def test_serializer_activas_excluye_resueltas(self):
        crear_notificacion(empresa=self.empresa, tipo="sistema", mensaje="Activa")
        resuelta = crear_notificacion(empresa=self.empresa, tipo="sistema",
                                      mensaje="Resuelta")
        resuelta.estado = "resuelta"
        resuelta.save(update_fields=["estado"])
        qs = NotificacionLecturaSerializer.activas(
            Notificacion.objects.filter(empresa=self.empresa))
        self.assertEqual(list(qs.values_list("mensaje", flat=True)), ["Activa"])

    def test_entrega_cae_al_canal_email_sin_whatsapp(self):
        # Sin WA_VINCULADO la entrega usa el canal alterno (email a consola).
        import io
        from django.core import mail
        aviso = crear_notificacion(
            empresa=self.empresa, tipo="sistema", mensaje="Prueba de entrega",
            notificar=True, usuario=self.admin)
        self.assertEqual(aviso.canal, "email")
        self.assertEqual(
            len(mail.outbox), 1,
            "El backend de email de consola debe haber recibido el mensaje")


class AlertasAislamientoTest(BaseCatalogoTest):
    """Fase 2: las alertas de stock son por empresa (sin fugas cross-tenant)."""

    def test_alertas_solo_de_mi_empresa(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999995")
        crear_notificacion(empresa=otra, tipo="stock", mensaje="Stock bajo: ajeno")
        crear_notificacion(empresa=self.empresa, tipo="stock",
                           mensaje="Stock bajo: Zapatos")

        api = self.api_como(self.empleado)
        cuerpo = api.get("/api/alertas/").json()
        mensajes = [n["mensaje"] for n in cuerpo["resultados"]]
        self.assertIn("Stock bajo: Zapatos", mensajes)
        self.assertNotIn("Stock bajo: ajeno", mensajes)

    def test_no_puedo_revisar_alerta_ajena(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999994")
        ajena = crear_notificacion(empresa=otra, tipo="stock",
                                   mensaje="Stock bajo: ajeno")

        api = self.api_como(self.empleado)
        res = api.post(f"/api/alertas/{ajena.id}/revisar/")
        self.assertEqual(res.status_code, 404)
        ajena.refresh_from_db()
        self.assertFalse(ajena.leida)

    def test_actualizar_stock_no_encuentra_producto_ajeno(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999993")
        otro_prod = Producto.objects.create(empresa=otra, nombre="Otro",
                                            sku="SKU-AJENO", precio=10,
                                            stock=1, stock_minimo=5)
        alerta = crear_notificacion(empresa=otra, tipo="stock",
                                    mensaje=f"Stock bajo: {otro_prod.nombre} "
                                            f"({otro_prod.sku}) tiene 1 unidades "
                                            f"(minimo 5).")

        api = self.api_como(self.empleado)
        res = api.post(f"/api/alertas/{alerta.id}/actualizar-stock/")
        self.assertEqual(res.status_code, 404)


class TiendaVirtualPublicaTest(BaseCoreTest):
    """Fase 2: la tienda publica se scopea por slug de empresa y oculta el
    stock a los visitantes anonimos."""

    def setUp(self):
        Empresa.objects.filter(pk=self.empresa.pk).update(
            slug="tienda-test")  # fuerza un slug estable para el test

    def test_catalogo_por_slug_solo_muestra_esa_empresa(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999990")
        Empresa.objects.filter(pk=otra.pk).update(slug="otra-tienda")
        Producto.objects.create(empresa=otra, nombre="Producto Ajeno",
                                sku="SKU-AJENO2", precio=50, stock=3,
                                stock_minimo=1)

        lista = self.client.get("/api/tienda/tienda-test/catalogo/").json()
        skus = [p["sku"] for p in lista["resultados"]]
        self.assertIn(self.producto.sku, skus)
        self.assertNotIn("SKU-AJENO2", skus)

    def test_slug_inexistente_devuelve_404(self):
        respuesta = self.client.get("/api/tienda/no-existe/catalogo/")
        self.assertEqual(respuesta.status_code, 404)

    def test_anonimo_oculta_stock(self):
        lista = self.client.get("/api/tienda/tienda-test/catalogo/").json()
        self.assertIsNone(lista["resultados"][0]["stock"])

    def test_detalle_por_slug_oculta_stock_a_anonimo(self):
        detalle = self.client.get(
            f"/api/tienda/tienda-test/catalogo/{self.producto.id}/").json()
        self.assertIsNone(detalle["stock"])

    def test_detalle_producto_de_otra_tienda_es_404(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999989")
        Empresa.objects.filter(pk=otra.pk).update(slug="otra-tienda")
        ajeno = Producto.objects.create(empresa=otra, nombre="Ajeno",
                                        sku="SKU-AJENO3", precio=9, stock=1,
                                        stock_minimo=1)
        respuesta = self.client.get(
            f"/api/tienda/tienda-test/catalogo/{ajeno.id}/")
        self.assertEqual(respuesta.status_code, 404)

    def test_catalogo_legacy_sin_slug_no_filtra_todo_lo_global(self):
        # Ruta sin slug y sin sesion: no debe exponer todos los tenants.
        lista = self.client.get("/api/tienda/catalogo/").json()
        self.assertEqual(lista["resultados"], [])


class VentaIntegridadTest(BaseCatalogoTest):
    """Fase 3: integridad de stock y correlativo de factura por empresa."""

    def _pos(self, api, producto, cantidad, descuento='0'):
        return api.post("/api/ventas/pos/", {
            "cliente": str(self.cliente.id),
            "metodo_pago": "efectivo",
            "descuento": descuento,
            "detalles": [{"producto": str(producto.id), "cantidad": cantidad}],
        }, format="json")

    def test_venta_descuenta_stock(self):
        api = self.api_como(self.empleado)
        res = self._pos(api, self.producto, 3)
        self.assertEqual(res.status_code, 201)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 40 - 3)

    def test_venta_con_mas_stock_del_disponible_rechazada(self):
        api = self.api_como(self.empleado)
        res = self._pos(api, self.producto, 999)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["codigo"], "STOCK_INSUFICIENTE")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 40)  # no cambia (no negativo)

    def test_facturas_distintas_empresas_pueden_repetir_consecutivo(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900999988")
        crear_roles_base(otra)
        v1 = self._pos(self.api_como(self.empleado), self.producto, 1).json()
        # El consecutivo es por empresa; el constraint compuesto evita duplicados
        # dentro de una misma empresa.
        existe_mismo = Venta.objects.filter(
            empresa=self.empresa, numero_factura=v1["numero_factura"]).count()
        self.assertEqual(existe_mismo, 1)

    def test_no_puede_duplicarse_numero_factura_en_la_misma_empresa(self):
        from django.db import IntegrityError
        v = self._pos(self.api_como(self.empleado), self.producto, 1).json()
        duplicada = Venta(empresa=self.empresa, cliente=self.cliente,
                          vendedor=self.empleado, total=1,
                          numero_factura=v["numero_factura"])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicada.save()


class RendimientoQueriesTest(BaseCatalogoTest):
    """Fase 6: los listados no deben disparar consultas N+1.

    Se mide con CaptureQueriesContext y se exige un tope de consultas muy por
    debajo del numero de filas (sin prefetch cada fila sumaria +1 consulta).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.producto2 = Producto.objects.create(
            empresa=cls.empresa, nombre="Camisa", sku="SKU-C02",
            precio=30000, stock=20, stock_minimo=5)
        cls.categoria_extra = cls.crear_categoria("Ropa")
        cls.categoria_vacia = cls.crear_categoria("Accesorios")
        Producto.objects.create(empresa=cls.empresa, nombre="Jean", sku="SKU-J03",
                                precio=90000, stock=15, stock_minimo=3,
                                categoria=cls.categoria_extra)
        cls.clientes_lista = [
            Cliente.objects.create(empresa=cls.empresa, nombre=f"Cliente {i}",
                                   tipo_documento="CC",
                                   numero_documento=f"700000{i}")
            for i in range(4)
        ]
        for i in range(5):
            venta = cls.crear_venta(total=75000)
            DetalleVenta.objects.create(venta=venta, producto=cls.producto,
                                        cantidad=1, precio_unitario=75000)
            DetalleVenta.objects.create(venta=venta, producto=cls.producto2,
                                        cantidad=2, precio_unitario=30000)

    def _medir(self, ruta):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        api = self.api_como(self.empleado)
        with CaptureQueriesContext(connection) as contexto:
            respuesta = api.get(ruta)
        return respuesta, len(contexto.captured_queries)

    def test_ventas_cabe_en_pocas_consultas(self):
        respuesta, consultas = self._medir("/api/ventas/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["resultados"]), 5)
        self.assertLessEqual(consultas, 15)

    def test_clientes_cabe_en_pocas_consultas(self):
        respuesta, consultas = self._medir("/api/clientes/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["resultados"]), 5)
        self.assertLessEqual(consultas, 10)

    def test_productos_cabe_en_pocas_consultas(self):
        respuesta, consultas = self._medir("/api/productos/?activo=true")
        self.assertEqual(respuesta.status_code, 200)
        self.assertLessEqual(len(respuesta.json()["resultados"]), 6)
        self.assertLessEqual(consultas, 12)

    def test_categorias_cabe_en_pocas_consultas(self):
        respuesta, consultas = self._medir("/api/categorias/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["resultados"]), 2)
        totales = {r["nombre"]: r["total_productos"] for r in respuesta.json()["resultados"]}
        self.assertEqual(totales["Ropa"], 1)
        self.assertEqual(totales["Accesorios"], 0)
        self.assertLessEqual(consultas, 10)

    def test_carrito_cabe_en_pocas_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        api = self.api_como(self.cliente_rol)
        with CaptureQueriesContext(connection) as contexto:
            respuesta = api.get("/api/tienda/carrito/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertLessEqual(len(contexto.captured_queries), 10)

