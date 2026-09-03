import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa

from .models import ActividadUsuario, Perfil, Rol, RolPermiso, TokenRecuperacion


class BaseCuentasTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Tienda Test", nit="900999999")

    @classmethod
    def crear_cuenta(cls, email="maria@test.co", password="Clave12345",
                     rol="EMPLEADO", activo=True):
        user = User.objects.create_user(username=email, email=email,
                                        password=password, first_name="Maria")
        perfil = Perfil.objects.create(usuario=user, empresa=cls.empresa,
                                       rol=Rol.de_nombre(rol))
        if not activo:
            user.is_active = False
            user.save()
        return user, perfil

    def login(self, email, password):
        return self.client.post(reverse("auth-login"),
                                {"email": email, "password": password},
                                content_type="application/json")


class RolesYPermisosTest(BaseCuentasTest):
    def test_seed_crea_tres_roles(self):
        call_command("seed_roles")
        nombres = set(Rol.objects.values_list("nombre", flat=True))
        self.assertEqual(nombres, {"ADMINISTRADOR", "EMPLEADO", "CLIENTE"})

    def test_seed_es_idempotente(self):
        call_command("seed_roles")
        total_antes = RolPermiso.objects.count()
        call_command("seed_roles")
        self.assertEqual(RolPermiso.objects.count(), total_antes)
        self.assertEqual(Rol.objects.count(), 3)

    def test_administrador_tiene_todos_los_permisos(self):
        call_command("seed_roles")
        _, perfil = self.crear_cuenta(rol="ADMINISTRADOR")
        self.assertTrue(perfil.tiene_permiso("usuarios.gestionar"))
        self.assertTrue(perfil.tiene_permiso("ventas.gestionar"))

    def test_empleado_no_gestiona_usuarios(self):
        call_command("seed_roles")
        _, perfil = self.crear_cuenta(rol="EMPLEADO")
        self.assertTrue(perfil.tiene_permiso("ventas.gestionar"))
        self.assertFalse(perfil.tiene_permiso("usuarios.gestionar"))


class LoginTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta()

    def test_login_exitoso_devuelve_tokens_y_rol(self):
        respuesta = self.login("maria@test.co", "Clave12345")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertIn("access", datos)
        self.assertIn("refresh", datos)
        self.assertEqual(datos["usuario"]["rol"], "EMPLEADO")
        self.assertEqual(datos["usuario"]["email"], "maria@test.co")

    def test_login_normaliza_email(self):
        respuesta = self.login("MARIA@TEST.CO", "Clave12345")
        self.assertEqual(respuesta.status_code, 200)

    def test_credenciales_invalidas_devuelve_401(self):
        respuesta = self.login("maria@test.co", "incorrecta")
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["codigo"], "CREDENCIALES_INVALIDAS")

    def test_correo_inexistente_no_revela_intentos(self):
        respuesta = self.login("fantasma@test.co", "loquesea123")
        self.assertEqual(respuesta.status_code, 401)
        self.assertIsNone(respuesta.json()["intentos_restantes"])

    def test_usuario_inactivo_devuelve_403(self):
        _, _ = self.crear_cuenta(email="inactivo@test.co", activo=False)
        respuesta = self.login("inactivo@test.co", "Clave12345")
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["codigo"], "USUARIO_INACTIVO")


class BloqueoPorIntentosTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta(email="luis@test.co")

    def test_bloqueo_tras_maximo_intentos(self):
        for intento in range(1, 6):
            respuesta = self.login("luis@test.co", f"mala-{intento}")
            if intento < 5:
                self.assertEqual(respuesta.status_code, 401)
                esperado = 5 - intento
                self.assertEqual(respuesta.json()["intentos_restantes"], esperado)
            else:
                self.assertEqual(respuesta.status_code, 423)
                self.assertEqual(respuesta.json()["codigo"], "CUENTA_BLOQUEADA")

    def test_password_correcto_no_entra_estando_bloqueado(self):
        for intento in range(5):
            self.login("luis@test.co", f"mala-{intento}")
        respuesta = self.login("luis@test.co", "Clave12345")
        self.assertEqual(respuesta.status_code, 423)

    def test_login_exitoso_reinicia_intentos(self):
        self.login("luis@test.co", "mala-1")
        self.login("luis@test.co", "Clave12345")
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.intentos_fallidos, 0)


class RecuperacionPasswordTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, _ = cls.crear_cuenta(email="ana@test.co")

    def solicitar(self, email="ana@test.co"):
        return self.client.post(reverse("auth-password-reset"),
                                {"email": email}, content_type="application/json")

    def extraer_token(self, cuerpo):
        coincidencia = re.search(r"token=([\w-]+)", cuerpo)
        return coincidencia.group(1) if coincidencia else None

    def test_solicitud_envia_correo_con_token(self):
        respuesta = self.solicitar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIsNotNone(self.extraer_token(mail.outbox[0].body))

    def test_email_desconocido_responde_igual_sin_correo(self):
        respuesta = self.solicitar("nadie@test.co")
        self.assertEqual(respuesta.status_code, 200)   # no se revela si existe
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmar_cambio_de_password(self):
        self.solicitar()
        token = self.extraer_token(mail.outbox[0].body)
        respuesta = self.client.post(
            reverse("auth-password-reset-confirmar"),
            {"token": token, "password": "NuevaClave99"},
            content_type="application/json")
        self.assertEqual(respuesta.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NuevaClave99"))
        # ademas desbloquea y limpia intentos
        perfil = self.user.perfil
        perfil.refresh_from_db()
        self.assertFalse(perfil.esta_bloqueado())

    def test_token_usado_no_vale_dos_veces(self):
        self.solicitar()
        token = self.extraer_token(mail.outbox[0].body)
        self.client.post(reverse("auth-password-reset-confirmar"),
                         {"token": token, "password": "NuevaClave99"},
                         content_type="application/json")
        respuesta = self.client.post(
            reverse("auth-password-reset-confirmar"),
            {"token": token, "password": "OtraClave77"},
            content_type="application/json")
        self.assertEqual(respuesta.json()["codigo"], "TOKEN_INVALIDO")

    def test_password_nueva_debe_ser_segura(self):
        self.solicitar()
        token = self.extraer_token(mail.outbox[0].body)
        respuesta = self.client.post(
            reverse("auth-password-reset-confirmar"),
            {"token": token, "password": "debil"},
            content_type="application/json")
        self.assertEqual(respuesta.status_code, 400)


class AuditoriaTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, _ = cls.crear_cuenta(email="audit@test.co")

    def test_login_exitoso_queda_registrado(self):
        self.login("audit@test.co", "Clave12345")
        self.assertTrue(ActividadUsuario.objects.filter(
            usuario=self.user, accion="LOGIN_EXITOSO").exists())

    def test_login_fallido_queda_registrado(self):
        self.login("audit@test.co", "equivocada")
        registro = ActividadUsuario.objects.filter(
            usuario=self.user, accion="LOGIN_FALLIDO").latest("fecha")
        self.assertIn("audit@test.co", registro.detalle)

    def test_intento_con_correo_inexistente_se_audita_anonimo(self):
        self.login("fantasma@test.co", "cualquier1")
        registro = ActividadUsuario.objects.filter(
            accion="LOGIN_FALLIDO", usuario__isnull=True).latest("fecha")
        self.assertIn("fantasma@test.co", registro.detalle)


class EmailUnicoTest(BaseCuentasTest):
    def test_bd_rechaza_emails_duplicados(self):
        User.objects.create_user(username="uno@test.co", email="repetido@test.co",
                                 password="Clave12345")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username="dos@test.co",
                                         email="REPETIDO@test.co",
                                         password="Clave12345")

    def test_endpoint_email_disponible(self):
        self.crear_cuenta(email="tomado@test.co")
        libre = self.client.get(reverse("auth-email-disponible"), {"email": "nuevo@test.co"})
        tomado = self.client.get(reverse("auth-email-disponible"), {"email": "tomado@test.co"})
        self.assertTrue(libre.json()["disponible"])
        self.assertFalse(tomado.json()["disponible"])

# ==================== FASE 2: administracion de seguridad ====================
from rest_framework.test import APIClient  # noqa: E402



class BaseSeguridadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Tienda Admin", nit="900888888")
        call_command("seed_roles")
        cls.admin = User.objects.create_user(username="admin@test.co", email="admin@test.co",
                                             password="Clave12345", first_name="Admin")
        Perfil.objects.create(usuario=cls.admin, empresa=cls.empresa,
                              rol=Rol.de_nombre("ADMINISTRADOR"), es_propietario=True)
        cls.api = APIClient()
        cls.api.force_authenticate(cls.admin)

    @classmethod
    def crear_cuenta_empresa(cls, email, rol="EMPLEADO", activo=True):
        user = User.objects.create_user(username=email, email=email,
                                        password="Clave12345", first_name="Empleado")
        perfil = Perfil.objects.create(usuario=user, empresa=cls.empresa,
                                       rol=Rol.de_nombre(rol))
        if not activo:
            user.is_active = False
            user.save()
        return user, perfil


class AccesoSeguridadTest(BaseSeguridadTest):
    def test_anonimo_recibe_401(self):
        respuesta = APIClient().get("/api/seguridad/usuarios/")
        self.assertEqual(respuesta.status_code, 401)

    def test_empleado_recibe_403(self):
        user, _ = self.crear_cuenta_empresa("emp@test.co")
        api = APIClient()
        api.force_authenticate(user)
        for ruta in ("/api/seguridad/usuarios/", "/api/seguridad/roles/", "/api/seguridad/permisos/"):
            self.assertEqual(api.get(ruta).status_code, 403, ruta)


class CrudUsuariosTest(BaseSeguridadTest):
    def test_crear_usuario(self):
        respuesta = self.api.post("/api/seguridad/usuarios/", {
            "nombre": "Nuevo Empleado", "email": "nuevo@test.co",
            "password": "Clave12345", "rol": "EMPLEADO"}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["rol"], "EMPLEADO")
        self.assertTrue(ActividadUsuario.objects.filter(accion="USUARIO_CREADO").exists())

    def test_email_duplicado_rechazado(self):
        self.crear_cuenta_empresa("ocupado@test.co")
        respuesta = self.api.post("/api/seguridad/usuarios/", {
            "nombre": "Duplicado", "email": "OCUPADO@test.co",
            "password": "Clave12345", "rol": "EMPLEADO"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Usa otro", str(respuesta.json()["errores"]))

    def test_rol_inexistente_rechazado(self):
        respuesta = self.api.post("/api/seguridad/usuarios/", {
            "nombre": "Sin Rol", "email": "sinrol@test.co",
            "password": "Clave12345", "rol": "JEFE"}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_password_debil_rechazada(self):
        respuesta = self.api.post("/api/seguridad/usuarios/", {
            "nombre": "Debil", "email": "debil@test.co",
            "password": "abc", "rol": "EMPLEADO"}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_editar_usuario_cambia_rol_y_correo(self):
        _, perfil = self.crear_cuenta_empresa("viejo@test.co")
        respuesta = self.api.put(f"/api/seguridad/usuarios/{perfil.id}/", {
            "nombre": "Renombrado", "email": "renombrado@test.co",
            "rol": "CLIENTE"}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["rol"], "CLIENTE")

    def test_patch_parcial_solo_rol(self):
        """Regresion: PATCH con un solo campo no debe fallar (fase 2)."""
        _, perfil = self.crear_cuenta_empresa("parcial@test.co")
        respuesta = self.api.patch(f"/api/seguridad/usuarios/{perfil.id}/",
                                   {"rol": "CLIENTE"}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["rol"], "CLIENTE")
        self.assertEqual(respuesta.json()["email"], "parcial@test.co")

    def test_editar_con_email_de_otro_rechazado(self):
        self.crear_cuenta_empresa("tomado@test.co")
        _, perfil = self.crear_cuenta_empresa("libre@test.co")
        respuesta = self.api.patch(f"/api/seguridad/usuarios/{perfil.id}/", {
            "email": "tomado@test.co"}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_desactivar_y_reactivar(self):
        _, perfil = self.crear_cuenta_empresa("temporal@test.co")
        r1 = self.api.post(f"/api/seguridad/usuarios/{perfil.id}/desactivar/")
        self.assertFalse(r1.json()["activo"])
        r2 = self.api.post(f"/api/seguridad/usuarios/{perfil.id}/reactivar/")
        self.assertTrue(r2.json()["activo"])
        self.assertTrue(ActividadUsuario.objects.filter(accion="USUARIO_DESACTIVADO").exists())

    def test_no_puede_desactivarse_a_si_mismo(self):
        mi_perfil = self.admin.perfil
        respuesta = self.api.post(f"/api/seguridad/usuarios/{mi_perfil.id}/desactivar/")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "AUTODESACTIVACION_PROHIBIDA")


class CrudRolesTest(BaseSeguridadTest):
    def test_listar_roles_con_permisos(self):
        respuesta = self.api.get("/api/seguridad/roles/")
        self.assertEqual(respuesta.status_code, 200)
        admin = next(r for r in respuesta.json()["resultados"] if r["nombre"] == "ADMINISTRADOR")
        # ADMINISTRADOR tiene TODOS los permisos: 8 gruesos (fase 1) + 11
        # finos (fase Empleados), ambos catalogos son aditivos.
        self.assertEqual(len(admin["permisos"]), 19)
        self.assertTrue(admin["es_sistema"])

    def test_catalogo_de_permisos(self):
        respuesta = self.api.get("/api/seguridad/permisos/")
        self.assertEqual(respuesta.json()["total"], 19)

    def test_crear_rol_con_permisos(self):
        respuesta = self.api.post("/api/seguridad/roles/", {
            "nombre": "SUPERVISOR", "descripcion": "Vigila ventas",
            "permisos": ["ventas.gestionar", "reportes.ver"]}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(sorted(respuesta.json()["permisos"]),
                         ["reportes.ver", "ventas.gestionar"])

    def test_permiso_inexistente_rechazado(self):
        respuesta = self.api.post("/api/seguridad/roles/", {
            "nombre": "FANTASMA", "permisos": ["no.existe"]}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_nombre_duplicado_rechazado(self):
        respuesta = self.api.post("/api/seguridad/roles/", {
            "nombre": "empleado", "permisos": []}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_editar_permisos_de_rol(self):
        _, _ = self.crear_cuenta_empresa("x@test.co")
        creado = self.api.post("/api/seguridad/roles/", {
            "nombre": "AUXILIAR", "permisos": []}, format="json").json()
        respuesta = self.api.patch(f"/api/seguridad/roles/{creado['id']}/", {
            "permisos": ["clientes.gestionar"]}, format="json")
        self.assertEqual(respuesta.json()["permisos"], ["clientes.gestionar"])

    def test_no_renombrar_rol_del_sistema(self):
        rol = Rol.objects.get(nombre="ADMINISTRADOR")
        respuesta = self.api.patch(f"/api/seguridad/roles/{rol.id}/", {
            "nombre": "JEFE_TOTAL"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "ROL_SISTEMA_LECTURA_ONLY")

    def test_eliminar_rol_sin_usuarios(self):
        creado = self.api.post("/api/seguridad/roles/", {
            "nombre": "PASANTE", "permisos": []}, format="json").json()
        respuesta = self.api.delete(f"/api/seguridad/roles/{creado['id']}/")
        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Rol.objects.filter(nombre="PASANTE").exists())

    def test_no_eliminar_rol_con_usuarios_activos(self):
        user = User.objects.create_user(username="conrol@test.co", email="conrol@test.co",
                                        password="Clave12345", first_name="Con Rol")
        Perfil.objects.create(usuario=user, empresa=self.empresa,
                              rol=Rol.de_nombre("AUXILIAR_VENTAS"))
        rol = Rol.objects.get(nombre="AUXILIAR_VENTAS")
        respuesta = self.api.delete(f"/api/seguridad/roles/{rol.id}/")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "ROL_CON_USUARIOS_ACTIVOS")
        self.assertIn("Reasignalos", respuesta.json()["detalle"])

    def test_no_eliminar_roles_del_sistema(self):
        for nombre in ("ADMINISTRADOR", "EMPLEADO", "CLIENTE"):
            rol = Rol.objects.get(nombre=nombre)
            respuesta = self.api.delete(f"/api/seguridad/roles/{rol.id}/")
            self.assertEqual(respuesta.json()["codigo"], "ROL_SISTEMA_LECTURA_ONLY")

    def test_clonar_rol_duplica_permisos_con_nombre_temporal(self):
        origen = Rol.objects.get(nombre="EMPLEADO")
        clon = self.api.post(f"/api/seguridad/roles/{origen.id}/clonar/").json()
        self.assertEqual(clon["nombre"], "EMPLEADO (COPIA)")
        self.assertEqual(sorted(clon["permisos"]), sorted(
            RolPermiso.objects.filter(rol=origen)
            .values_list("permiso__codigo", flat=True)))
        # segundo clon recibe nombre distinto
        otro = self.api.post(f"/api/seguridad/roles/{origen.id}/clonar/").json()
        self.assertNotEqual(clon["nombre"], otro["nombre"])

    def test_acciones_quedan_auditadas(self):
        self.api.post("/api/seguridad/usuarios/", {
            "nombre": "Auditado", "email": "auditado@test.co",
            "password": "Clave12345", "rol": "EMPLEADO"}, format="json")
        creado = self.api.post("/api/seguridad/roles/", {
            "nombre": "AUDITADO", "permisos": []}, format="json").json()
        self.api.post(f"/api/seguridad/roles/{creado['id']}/clonar/")
        self.api.delete(f"/api/seguridad/roles/{creado['id']}/")

        acciones = set(ActividadUsuario.objects.values_list("accion", flat=True))
        esperadas = {"USUARIO_CREADO", "ROL_CREADO", "ROL_ELIMINADO", "ROL_CLONADO"}
        faltantes = esperadas - acciones
        self.assertEqual(faltantes, set(), f"Faltan auditorias: {faltantes}")


class AislamientoRolesTenantTest(TestCase):
    """Regresion: los roles personalizados de una empresa no deben ser
    visibles ni modificables por los administradores de otra empresa."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")
        cls.empresa_a = Empresa.objects.create(nombre="Tienda A", nit="900111111")
        cls.empresa_b = Empresa.objects.create(nombre="Tienda B", nit="900222222")

        cls.admin_a = User.objects.create_user(username="admina@test.co",
                                               email="admina@test.co",
                                               password="Clave12345", first_name="Admin A")
        Perfil.objects.create(usuario=cls.admin_a, empresa=cls.empresa_a,
                              rol=Rol.de_nombre("ADMINISTRADOR"), es_propietario=True)

        cls.admin_b = User.objects.create_user(username="adminb@test.co",
                                               email="adminb@test.co",
                                               password="Clave12345", first_name="Admin B")
        Perfil.objects.create(usuario=cls.admin_b, empresa=cls.empresa_b,
                              rol=Rol.de_nombre("ADMINISTRADOR"), es_propietario=True)

        cls.api_a = APIClient()
        cls.api_a.force_authenticate(cls.admin_a)
        cls.api_b = APIClient()
        cls.api_b.force_authenticate(cls.admin_b)

    def test_dos_empresas_pueden_tener_roles_de_mismo_nombre(self):
        # La empresa A crea un rol "SUPERVISOR"
        creado = self.api_a.post("/api/seguridad/roles/", {
            "nombre": "SUPERVISOR", "permisos": ["ventas.gestionar"]}, format="json")
        self.assertEqual(creado.status_code, 201)

        # La empresa B puede crear otro "SUPERVISOR" sin colision
        creado_b = self.api_b.post("/api/seguridad/roles/", {
            "nombre": "SUPERVISOR", "permisos": ["reportes.ver"]}, format="json")
        self.assertEqual(creado_b.status_code, 201)

        # Ambos sobreviven en la base y son distintos
        self.assertEqual(Rol.objects.filter(nombre="SUPERVISOR").count(), 2)

    def test_empresa_b_no_ve_los_roles_personalizados_de_empresa_a(self):
        creado = self.api_a.post("/api/seguridad/roles/", {
            "nombre": "GERENTE", "permisos": []}, format="json").json()

        lista = self.api_b.get("/api/seguridad/roles/").json()
        nombres = [r["nombre"] for r in lista["resultados"]]
        self.assertNotIn("GERENTE", nombres)

        # La empresa B no puede consultar ni modificar el rol de la empresa A
        detalle = self.api_b.get(f"/api/seguridad/roles/{creado['id']}/")
        self.assertEqual(detalle.status_code, 404)
        edicion = self.api_b.patch(f"/api/seguridad/roles/{creado['id']}/",
                                   {"permisos": ["reportes.ver"]}, format="json")
        self.assertEqual(edicion.status_code, 404)
        borrado = self.api_b.delete(f"/api/seguridad/roles/{creado['id']}/")
        self.assertEqual(borrado.status_code, 404)

        # El rol sigue intacto para la empresa A
        detalle_a = self.api_a.get(f"/api/seguridad/roles/{creado['id']}/")
        self.assertEqual(detalle_a.status_code, 200)

    def test_empresa_b_no_clona_rol_de_empresa_a(self):
        creado = self.api_a.post("/api/seguridad/roles/", {
            "nombre": "JEFE", "permisos": []}, format="json").json()
        clon = self.api_b.post(f"/api/seguridad/roles/{creado['id']}/clonar/")
        self.assertEqual(clon.status_code, 404)

    def test_admin_b_no_asigna_rol_de_empresa_a_a_sus_usuarios(self):
        self.api_a.post("/api/seguridad/roles/", {
            "nombre": "SECRETARIA", "permisos": []}, format="json")
        respuesta = self.api_b.post("/api/seguridad/usuarios/", {
            "nombre": "Nuevo B", "email": "nuevob@test.co",
            "password": "Clave12345", "rol": "SECRETARIA"}, format="json")
        self.assertEqual(respuesta.status_code, 400)

class RendimientoQueriesRolesTest(BaseSeguridadTest):
    def test_listado_roles_cabe_en_pocas_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.crear_cuenta_empresa("emp1@test.co")
        self.crear_cuenta_empresa("emp2@test.co", rol="CLIENTE")
        with CaptureQueriesContext(connection) as contexto:
            respuesta = self.api.get("/api/seguridad/roles/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertGreaterEqual(len(respuesta.json()["resultados"]), 3)
        self.assertLessEqual(len(contexto.captured_queries), 10)


# ==================== FASE 5: JWT, /me, refresh y token reset ================

from rest_framework_simplejwt.tokens import RefreshToken   # noqa: E402


class JWTyMeTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, _ = cls.crear_cuenta(email="jwt@test.co")

    def obtener_tokens(self):
        respuesta = self.login("jwt@test.co", "Clave12345")
        return respuesta.json()

    def test_me_devuelve_perfil_y_permisos(self):
        tokens = self.obtener_tokens()
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        respuesta = api.get(reverse("auth-me"))
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["email"], "jwt@test.co")
        self.assertEqual(datos["rol"], "EMPLEADO")
        self.assertIn("permisos", datos)
        self.assertIn("empresa_nombre", datos)

    def test_me_con_token_invalido_devuelve_401(self):
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION="Bearer token-falso-invalido")
        respuesta = api.get(reverse("auth-me"))
        self.assertEqual(respuesta.status_code, 401)

    def test_me_sin_token_devuelve_401(self):
        respuesta = APIClient().get(reverse("auth-me"))
        self.assertEqual(respuesta.status_code, 401)

    def test_me_con_token_expirado_devuelve_401(self):
        # Forzamos un access token con 'exp' en el pasado para probar la
        # ruta "expirado" de simplejwt sin esperar 30 minutos.
        tokens = self.obtener_tokens()
        refresh = RefreshToken(tokens["refresh"])
        access = refresh.access_token
        access["exp"] = timezone.now().timestamp() - 60
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}")
        respuesta = api.get(reverse("auth-me"))
        self.assertEqual(respuesta.status_code, 401)


class RefreshTokenTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, _ = cls.crear_cuenta(email="refresh@test.co")

    def get_client(self):
        return self.client

    def test_refresh_devuelve_nuevo_access(self):
        tokens = self.login("refresh@test.co", "Clave12345").json()
        respuesta = self.client.post(reverse("auth-refresh"),
                                     {"refresh": tokens["refresh"]},
                                     content_type="application/json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.json())

    def test_refresh_con_token_invalido_devuelve_401(self):
        respuesta = self.client.post(reverse("auth-refresh"),
                                     {"refresh": "no-es-un-token"},
                                     content_type="application/json")
        self.assertEqual(respuesta.status_code, 401)

    def test_refresh_con_body_invalido_devuelve_400(self):
        respuesta = self.client.post(reverse("auth-refresh"),
                                     {}, content_type="application/json")
        # Falta el campo refresh -> validacion de DRF (error de peticion).
        self.assertIn(respuesta.status_code, (400,))

    def test_access_tokens_dan_acceso_a_datos_protegidos(self):
        tokens = self.login("refresh@test.co", "Clave12345").json()
        respuesta = self.client.get(
            "/api/seguridad/roles/",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        # Como es EMPLEADO no puede ver roles -> 403 (autenticado pero sin
        # permiso). Lo importante es que NO sea 401.
        self.assertEqual(respuesta.status_code, 403)


class RecuperacionTokenExpiradoTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, _ = cls.crear_cuenta(email="expirado@test.co")

    def solicitar(self):
        return self.client.post(reverse("auth-password-reset"),
                                {"email": "expirado@test.co"},
                                content_type="application/json")

    def extraer_token(self, cuerpo):
        coincidencia = re.search(r"token=([\w-]+)", cuerpo)
        return coincidencia.group(1) if coincidencia else None

    def test_restablecer_con_token_expirado_devuelve_400(self):
        self.solicitar()
        token = self.extraer_token(mail.outbox[0].body)
        registro = TokenRecuperacion.objects.get(
            token_hash=TokenRecuperacion.calcular_hash(token))
        registro.expira = timezone.now() - timedelta(minutes=1)
        registro.save(update_fields=["expira"])

        respuesta = self.client.post(
            reverse("auth-password-reset-confirmar"),
            {"token": token, "password": "NuevaClave99"},
            content_type="application/json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "TOKEN_INVALIDO")

    def test_restablecer_con_token_inexistente_devuelve_400(self):
        respuesta = self.client.post(
            reverse("auth-password-reset-confirmar"),
            {"token": "token-que-no-existe", "password": "NuevaClave99"},
            content_type="application/json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "TOKEN_INVALIDO")
