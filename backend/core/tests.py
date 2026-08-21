from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (Categoria, Cliente, DetalleVenta, Empresa, MovimientoInventario,
                     Notificacion, Producto, Venta)


class BaseCoreTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Tienda Test", nit="900999998")
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
                              rol=Rol.de_nombre("ADMINISTRADOR"))
        cls.empleado = User.objects.create_user(username="empleado@test.co",
                                                email="empleado@test.co",
                                                password="Clave12345")
        Perfil.objects.create(usuario=cls.empleado, empresa=cls.empresa,
                              rol=Rol.de_nombre("EMPLEADO"))
        cls.cliente_rol = User.objects.create_user(username="solo@test.co",
                                                   email="solo@test.co",
                                                   password="Clave12345")
        cls.perfil_cliente_rol = Perfil.objects.create(
            usuario=cls.cliente_rol, empresa=cls.empresa,
            rol=Rol.de_nombre("CLIENTE"))

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
