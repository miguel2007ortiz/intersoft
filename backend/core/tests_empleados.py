from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from cuentas.models import Perfil, Rol

from .models import Empresa


class BaseEmpleadosTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")
        cls.empresa = Empresa.objects.create(nombre="Tienda Empleados", nit="900777777")
        cls.admin = User.objects.create_user(username="admin@emp.co", email="admin@emp.co",
                                             password="Clave12345", first_name="Ana", last_name="Admin")
        Perfil.objects.create(usuario=cls.admin, empresa=cls.empresa,
                              rol=Rol.de_nombre("ADMINISTRADOR"), es_propietario=True)
        cls.api = APIClient()
        cls.api.force_authenticate(cls.admin)

    @classmethod
    def crear_empleado_directo(cls, email, rol="EMPLEADO", activo=True, empresa=None,
                               tipo_documento=None, numero_documento=None):
        user = User.objects.create_user(username=email, email=email, password="Clave12345",
                                        first_name="Emp", last_name=email.split("@")[0])
        perfil = Perfil.objects.create(usuario=user, empresa=empresa or cls.empresa,
                                       rol=Rol.de_nombre(rol),
                                       tipo_documento=tipo_documento,
                                       numero_documento=numero_documento)
        if not activo:
            user.is_active = False
            user.save()
        return user, perfil

    DATOS = {"nombre": "Carlos Perez", "email": "carlos.perez@emp.co",
            "rol": "EMPLEADO", "tipo_documento": "CC", "numero_documento": "700111222",
            "telefono": "3001234567", "cargo": "Cajero"}


class AccesoEmpleadosTest(BaseEmpleadosTest):
    def test_anonimo_recibe_401(self):
        respuesta = APIClient().get("/api/empleados/")
        self.assertEqual(respuesta.status_code, 401)

    def test_empleado_sin_permiso_recibe_403(self):
        user, _ = self.crear_empleado_directo("emp@emp.co")
        api = APIClient()
        api.force_authenticate(user)
        self.assertEqual(api.get("/api/empleados/").status_code, 403)
        self.assertEqual(api.post("/api/empleados/", self.DATOS, format="json").status_code, 403)


class CrearEmpleadoTest(BaseEmpleadosTest):
    def test_crear_empleado_genera_password_temporal(self):
        respuesta = self.api.post("/api/empleados/", self.DATOS, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        cuerpo = respuesta.json()
        self.assertIn("password_temporal", cuerpo)
        self.assertTrue(cuerpo["activo"])

        perfil = Perfil.objects.get(usuario__email="carlos.perez@emp.co")
        self.assertTrue(perfil.debe_cambiar_password)
        self.assertTrue(perfil.usuario.check_password(cuerpo["password_temporal"]))

    def test_crear_empleado_con_password_propia_no_la_expone(self):
        datos = {**self.DATOS, "password": "ClaveManual99"}
        respuesta = self.api.post("/api/empleados/", datos, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        self.assertNotIn("password_temporal", respuesta.json())

    def test_documento_duplicado_activo_rechazado(self):
        self.crear_empleado_directo("previo@emp.co", tipo_documento="CC",
                                    numero_documento="700111222")
        respuesta = self.api.post("/api/empleados/", self.DATOS, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("numero_documento", respuesta.json()["errores"])

    def test_documento_duplicado_inactivo_ofrece_reactivar(self):
        _, inactivo = self.crear_empleado_directo("previo@emp.co", tipo_documento="CC",
                                                   numero_documento="700111222", activo=False)
        respuesta = self.api.post("/api/empleados/", self.DATOS, format="json")
        self.assertEqual(respuesta.status_code, 400)
        id_ofrecido = respuesta.json()["errores"]["empleado_inactivo_id"]
        if isinstance(id_ofrecido, list):
            id_ofrecido = id_ofrecido[0]
        self.assertEqual(id_ofrecido, str(inactivo.id))

    def test_rol_cliente_rechazado(self):
        datos = {**self.DATOS, "rol": "CLIENTE"}
        respuesta = self.api.post("/api/empleados/", datos, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("rol", respuesta.json()["errores"])

    def test_no_ve_empleados_de_otra_empresa(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900777778")
        _, perfil_ajeno = self.crear_empleado_directo("ajeno@otra.co", empresa=otra)
        respuesta = self.api.get(f"/api/empleados/{perfil_ajeno.id}/")
        self.assertEqual(respuesta.status_code, 404)


class EstadoEmpleadoTest(BaseEmpleadosTest):
    def test_no_puede_desactivarse_a_si_mismo(self):
        respuesta = self.api.post(f"/api/empleados/{self.admin.perfil.id}/desactivar/")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "AUTODESACTIVACION_PROHIBIDA")

    def test_no_puede_quedar_sin_ningun_administrador(self):
        # self.admin es el unico ADMINISTRADOR activo de la empresa.
        _, otro_admin = self.crear_empleado_directo("otro.admin@emp.co", rol="ADMINISTRADOR")
        api_otro = APIClient()
        api_otro.force_authenticate(otro_admin.usuario)

        r1 = api_otro.post(f"/api/empleados/{self.admin.perfil.id}/desactivar/")
        self.assertEqual(r1.status_code, 200)   # si hay 2 admins, se puede

        # self.admin ya quedo inactivo; otro_admin es ahora el ultimo activo.
        # self.api (autenticado como self.admin) intenta desactivarlo: no es
        # autodesactivacion (actor != objetivo), asi que aqui se prueba
        # especificamente el guardado de UNICO_ADMINISTRADOR.
        r2 = self.api.post(f"/api/empleados/{otro_admin.id}/desactivar/")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.json()["codigo"], "UNICO_ADMINISTRADOR")

    def test_desactivar_reactivar_idempotente(self):
        user, perfil = self.crear_empleado_directo("temp@emp.co")
        r1 = self.api.post(f"/api/empleados/{perfil.id}/desactivar/")
        self.assertEqual(r1.status_code, 200)
        self.assertFalse(r1.json()["activo"])
        r2 = self.api.post(f"/api/empleados/{perfil.id}/desactivar/")
        self.assertEqual(r2.status_code, 200)   # repetir no rompe
        r3 = self.api.post(f"/api/empleados/{perfil.id}/reactivar/")
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.json()["activo"])


class PasswordEmpleadoTest(BaseEmpleadosTest):
    def test_regenerar_password_fuerza_cambio(self):
        user, perfil = self.crear_empleado_directo("olvido@emp.co")
        respuesta = self.api.post(f"/api/empleados/{perfil.id}/password/")
        self.assertEqual(respuesta.status_code, 200)
        nueva = respuesta.json()["password_temporal"]
        perfil.refresh_from_db()
        user.refresh_from_db()
        self.assertTrue(perfil.debe_cambiar_password)
        self.assertTrue(user.check_password(nueva))


class ListarEmpleadosTest(BaseEmpleadosTest):
    def setUp(self):
        for i, email in enumerate(["ana@emp.co", "bety@emp.co", "carlos@emp.co"]):
            self.crear_empleado_directo(email, rol="EMPLEADO")
        self.crear_empleado_directo("inactivo@emp.co", activo=False)

    def test_lista_activos_por_defecto_excluye_inactivos(self):
        respuesta = self.api.get("/api/empleados/")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual(cuerpo["total"], 4)  # admin (Ana) + 3 activos
        emails = {r["email"] for r in cuerpo["resultados"]}
        self.assertNotIn("inactivo@emp.co", emails)

    def test_filtro_estado_inactivos(self):
        respuesta = self.api.get("/api/empleados/?estado=inactivos")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["total"], 1)

    def test_filtro_estado_todos(self):
        respuesta = self.api.get("/api/empleados/?estado=todos")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["total"], 5)  # admin (creado en setUpTestData) + 3 + inactivo

    def test_busqueda_por_nombre_apellido_email(self):
        respuesta = self.api.get("/api/empleados/?busqueda=ana")
        self.assertEqual(respuesta.status_code, 200)
        emails = {r["email"] for r in respuesta.json()["resultados"]}
        # admin (first_name "Ana") + ana@emp.co (last_name "ana")
        self.assertIn("admin@emp.co", emails)
        self.assertIn("ana@emp.co", emails)

    def test_busqueda_por_documento(self):
        self.crear_empleado_directo("doc@emp.co", tipo_documento="CC",
                                    numero_documento="987654321")
        respuesta = self.api.get("/api/empleados/?busqueda=987654321")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["total"], 1)
        self.assertEqual(respuesta.json()["resultados"][0]["email"], "doc@emp.co")

    def test_pagina_mas_alla_del_final_devuelve_lista_vacia(self):
        respuesta = self.api.get("/api/empleados/?pagina=99")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["pagina"], 99)
        self.assertEqual(respuesta.json()["resultados"], [])

    def test_pagina_no_numerica_vuelve_a_pagina_1(self):
        respuesta = self.api.get("/api/empleados/?pagina=abc")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["pagina"], 1)


class DetalleEmpleadoOperacionesTest(BaseEmpleadosTest):
    def test_get_detalle_404_para_ajeno(self):
        otra = Empresa.objects.create(nombre="Otra", nit="900777779")
        _, perfil = self.crear_empleado_directo("ajeno@otra.co", empresa=otra)
        respuesta = self.api.get(f"/api/empleados/{perfil.id}/")
        self.assertEqual(respuesta.status_code, 404)

    def test_get_detalle_incluye_vendedor_datos(self):
        user, perfil = self.crear_empleado_directo("vend@emp.co")
        respuesta = self.api.get(f"/api/empleados/{perfil.id}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["email"], "vend@emp.co")

    def test_patch_actualiza_cargo(self):
        user, perfil = self.crear_empleado_directo("edi@emp.co")
        respuesta = self.api.patch(f"/api/empleados/{perfil.id}/", {"cargo": "Cajero jefe"}, format="json")
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        perfil.refresh_from_db()
        self.assertEqual(perfil.cargo, "Cajero jefe")

    def test_put_invalido_devuelve_datos_invalidos(self):
        user, perfil = self.crear_empleado_directo("edi2@emp.co")
        respuesta = self.api.put(f"/api/empleados/{perfil.id}/", {"rol": "INEXISTENTE"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "DATOS_INVALIDOS")

    def test_quitar_ultimo_admin_via_patch_bloqueado(self):
        # self.admin (Ana) y otro son admins. Con otro desactivo a Ana, dejo a
        # otro como unico admin activo, y usando la sesion de Ana intento
        # des-rolearle via PATCH -> UNICO_ADMINISTRADOR.
        _, otro_admin = self.crear_empleado_directo("otroadmin@emp.co", rol="ADMINISTRADOR")
        api_otro = APIClient()
        api_otro.force_authenticate(otro_admin.usuario)
        r = api_otro.post(f"/api/empleados/{self.admin.perfil.id}/desactivar/")
        self.assertEqual(r.status_code, 200)
        r = self.api.patch(f"/api/empleados/{otro_admin.id}/",
                           {"rol": "EMPLEADO"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "UNICO_ADMINISTRADOR")

    def test_delete_desactiva_empleado(self):
        user, perfil = self.crear_empleado_directo("del@emp.co")
        respuesta = self.api.delete(f"/api/empleados/{perfil.id}/")
        self.assertEqual(respuesta.status_code, 204)
        perfil.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(perfil.usuario.is_active)
        self.assertIsNotNone(perfil.deleted_at)

    def test_delete_sin_permisos_403(self):
        cliente, _ = self.crear_empleado_directo("cliente@emp.co", rol="CLIENTE")
        api = APIClient()
        api.force_authenticate(cliente)
        _, objetivo = self.crear_empleado_directo("objetivo@emp.co")
        respuesta = api.delete(f"/api/empleados/{objetivo.id}/")
        self.assertEqual(respuesta.status_code, 403)

    def test_delete_self_bloqueado(self):
        respuesta = self.api.delete(f"/api/empleados/{self.admin.perfil.id}/")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "AUTODESACTIVACION_PROHIBIDA")

    def test_delete_ultimo_admin_bloqueado(self):
        # Hay dos admins (self.admin y otro). Con otro, desactivo a self.admin
        # (permitido, queda 1 admin activo). Con self.api (que sigue siendo
        # self.admin, inactivo pero con sesion vigente) intento borrar a otro,
        # que es ahora el unico admin activo -> UNICO_ADMINISTRADOR.
        _, otro = self.crear_empleado_directo("otroadmin@emp.co", rol="ADMINISTRADOR")
        r = self.api.post(f"/api/empleados/{self.admin.perfil.id}/desactivar/")
        self.assertEqual(r.status_code, 400)  # primera comprobacion: ultimo admin
        api_otro = APIClient()
        api_otro.force_authenticate(otro.usuario)
        r = api_otro.post(f"/api/empleados/{self.admin.perfil.id}/desactivar/")
        self.assertEqual(r.status_code, 200)
        r = self.api.delete(f"/api/empleados/{otro.id}/")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "UNICO_ADMINISTRADOR")
