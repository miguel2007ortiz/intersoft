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
