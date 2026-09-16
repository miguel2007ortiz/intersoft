import re
import time
from datetime import timedelta
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa

from .identidad import buscar, describir
from .models import ActividadUsuario, Perfil, Permiso, Rol, RolPermiso, TokenRecuperacion
from .permissions import EsAdministrador, EsPersonal


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


class PermisosClasesTest(BaseCuentasTest):
    """Regresion: EsAdministrador/EsPersonal solo comparaban
    perfil.rol.nombre contra literales fijos, asi que un rol personalizado
    por-empresa (feature soportada por el modelo Rol) nunca pasaba, sin
    importar los permisos reales que tuviera asignados."""

    def _request_con_perfil(self, perfil):
        return SimpleNamespace(user=SimpleNamespace(perfil=perfil))

    def test_rol_personalizado_con_permiso_de_usuarios_pasa_es_administrador(self):
        call_command("seed_roles")
        rol_gerente = Rol.objects.create(nombre="GERENTE", empresa=self.empresa)
        RolPermiso.objects.create(
            rol=rol_gerente, permiso=Permiso.objects.get(codigo="usuarios.gestionar"))
        user = User.objects.create_user(username="g@test.co", email="g@test.co",
                                        password="Clave12345")
        perfil = Perfil.objects.create(usuario=user, empresa=self.empresa, rol=rol_gerente)
        self.assertTrue(
            EsAdministrador().has_permission(self._request_con_perfil(perfil), None))

    def test_rol_personalizado_sin_permisos_no_pasa_es_administrador(self):
        call_command("seed_roles")
        rol_vacio = Rol.objects.create(nombre="AUDITOR", empresa=self.empresa)
        user = User.objects.create_user(username="a@test.co", email="a@test.co",
                                        password="Clave12345")
        perfil = Perfil.objects.create(usuario=user, empresa=self.empresa, rol=rol_vacio)
        self.assertFalse(
            EsAdministrador().has_permission(self._request_con_perfil(perfil), None))

    def test_rol_personalizado_con_algun_permiso_pasa_es_personal(self):
        call_command("seed_roles")
        rol_cajero = Rol.objects.create(nombre="CAJERO", empresa=self.empresa)
        RolPermiso.objects.create(
            rol=rol_cajero, permiso=Permiso.objects.get(codigo="ventas.gestionar"))
        user = User.objects.create_user(username="c@test.co", email="c@test.co",
                                        password="Clave12345")
        perfil = Perfil.objects.create(usuario=user, empresa=self.empresa, rol=rol_cajero)
        self.assertTrue(
            EsPersonal().has_permission(self._request_con_perfil(perfil), None))

    def test_rol_cliente_sin_permisos_no_pasa_es_personal(self):
        _, perfil = self.crear_cuenta(rol="CLIENTE")
        self.assertFalse(
            EsPersonal().has_permission(self._request_con_perfil(perfil), None))

    def test_perfil_con_rol_none_no_revienta(self):
        """rol es PROTECT y no-nulo en el modelo, pero un perfil mal
        migrado/creado a mano puede tener rol_id colgante; antes
        perfil.rol lanzaba AttributeError (500) en vez de negar el acceso."""
        perfil_sin_rol = SimpleNamespace(deleted_at=None, rol=None)
        request = self._request_con_perfil(perfil_sin_rol)
        self.assertFalse(EsAdministrador().has_permission(request, None))
        self.assertFalse(EsPersonal().has_permission(request, None))


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
        self.assertNotIn("intentos_restantes", respuesta.json())

    def test_usuario_inactivo_no_se_distingue_de_credenciales_malas(self):
        """Una cuenta desactivada responde el 401 generico: devolver
        USUARIO_INACTIVO antes de validar la contrasena delataba que el
        correo estaba registrado (BUG-19)."""
        _, _ = self.crear_cuenta(email="inactivo@test.co", activo=False)
        respuesta = self.login("inactivo@test.co", "Clave12345")
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["codigo"], "CREDENCIALES_INVALIDAS")


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
                # El cuerpo nunca dice cuantos intentos quedan (BUG-19).
                self.assertNotIn("intentos_restantes", respuesta.json())
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
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["codigo"], "ROL_DEL_SISTEMA")

    def test_eliminar_rol_sin_usuarios(self):
        creado = self.api.post("/api/seguridad/roles/", {
            "nombre": "PASANTE", "permisos": []}, format="json").json()
        respuesta = self.api.delete(f"/api/seguridad/roles/{creado['id']}/")
        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Rol.objects.filter(nombre="PASANTE").exists())

    def test_no_eliminar_rol_con_usuarios_activos(self):
        user = User.objects.create_user(username="conrol@test.co", email="conrol@test.co",
                                        password="Clave12345", first_name="Con Rol")
        # Rol PROPIO de la empresa: `Rol.de_nombre` crearia uno global y esos
        # ahora responden 403 antes de mirar si estan en uso.
        rol = Rol.objects.create(nombre="AUXILIAR_VENTAS", empresa=self.empresa)
        Perfil.objects.create(usuario=user, empresa=self.empresa, rol=rol)
        respuesta = self.api.delete(f"/api/seguridad/roles/{rol.id}/")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "ROL_CON_USUARIOS_ACTIVOS")
        self.assertIn("Reasignalos", respuesta.json()["detalle"])

    def test_no_eliminar_roles_del_sistema(self):
        for nombre in ("ADMINISTRADOR", "EMPLEADO", "CLIENTE"):
            rol = Rol.objects.get(nombre=nombre)
            respuesta = self.api.delete(f"/api/seguridad/roles/{rol.id}/")
            self.assertEqual(respuesta.json()["codigo"], "ROL_DEL_SISTEMA")

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


# ============ BUG-09: identidad unica en el login (sin ambiguedad) ============

class IdentidadLoginTest(BaseCuentasTest):
    """El token, el perfil y el contexto (empresa, rol, permisos) tienen que
    salir todos del MISMO usuario. Antes el perfil se elegia por correo con
    `Perfil.objects.filter(usuario__email__iexact=...)` y podia no ser el del
    usuario que `authenticate()` habia validado."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.empresa_b = Empresa.objects.create(nombre="Otra SAS", nit="900888888")
        cls.user_a, cls.perfil_a = cls.crear_cuenta(email="ana@empresa-a.co",
                                                    rol="ADMINISTRADOR")
        cls.user_b = User.objects.create_user(username="beto@empresa-b.co",
                                              email="beto@empresa-b.co",
                                              password="Clave12345", first_name="Beto")
        cls.perfil_b = Perfil.objects.create(usuario=cls.user_b, empresa=cls.empresa_b,
                                             rol=Rol.de_nombre("EMPLEADO"))

    def test_login_devuelve_id_de_user_y_perfil_id_aparte(self):
        datos = self.login("ana@empresa-a.co", "Clave12345").json()["usuario"]
        self.assertEqual(datos["id"], str(self.user_a.id))
        self.assertEqual(datos["perfil_id"], str(self.perfil_a.id))

    def test_token_y_contexto_son_del_mismo_usuario(self):
        cuerpo = self.login("beto@empresa-b.co", "Clave12345").json()
        self.assertEqual(cuerpo["usuario"]["id"], str(self.user_b.id))
        self.assertEqual(cuerpo["usuario"]["empresa"], str(self.empresa_b.id))
        self.assertEqual(cuerpo["usuario"]["rol"], "EMPLEADO")

        # El contexto de /auth/me/ (fuente de permisos del frontend) tiene que
        # describir al mismo usuario que emitio el token.
        cabecera = "Bearer " + cuerpo["access"]
        me = self.client.get(reverse("auth-me"),
                             HTTP_AUTHORIZATION=cabecera).json()
        self.assertEqual(me["id"], str(self.user_b.id))
        self.assertEqual(me["perfil_id"], str(self.perfil_b.id))
        self.assertEqual(me["empresa"], str(self.empresa_b.id))
        self.assertEqual(me["rol"], "EMPLEADO")
        permisos_del_rol = set(RolPermiso.objects
                               .filter(rol=self.perfil_b.rol)
                               .values_list("permiso__codigo", flat=True))
        self.assertEqual(set(me["permisos"]), permisos_del_rol)

    def test_fallos_contra_una_empresa_no_bloquean_la_cuenta_de_otra(self):
        for intento in range(6):
            self.login("ana@empresa-a.co", "mala-%d" % intento)

        self.perfil_a.refresh_from_db()
        self.perfil_b.refresh_from_db()
        self.assertTrue(self.perfil_a.esta_bloqueado())
        self.assertEqual(self.perfil_b.intentos_fallidos, 0)
        self.assertFalse(self.perfil_b.esta_bloqueado())
        self.assertEqual(self.login("beto@empresa-b.co", "Clave12345").status_code, 200)


class VerificacionEmailsDuplicadosTest(TestCase):
    def test_comando_pasa_sin_duplicados(self):
        User.objects.create_user(username="uno@test.co", email="uno@test.co",
                                 password="Clave12345")
        call_command("verificar_emails_duplicados")  # no levanta CommandError


# ================= BUG-19: el login no permite enumerar correos ==============

class AntiEnumeracionLoginTest(BaseCuentasTest):
    REGISTRADO = "registrada@test.co"
    INEXISTENTE = "no-existe@test.co"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta(email=cls.REGISTRADO)

    def setUp(self):
        cache.clear()
        self.reiniciar_intentos()

    def reiniciar_intentos(self):
        Perfil.objects.filter(pk=self.perfil.pk).update(intentos_fallidos=0,
                                                        fecha_desbloqueo=None)

    def test_401_identico_exista_o_no_el_correo(self):
        real = self.login(self.REGISTRADO, "contrasena-mala")
        falso = self.login(self.INEXISTENTE, "contrasena-mala")
        self.assertEqual(real.status_code, 401)
        self.assertEqual(falso.status_code, 401)
        self.assertEqual(real.json(), falso.json())
        self.assertNotIn("intentos_restantes", real.json())

    def test_aviso_generico_en_el_ultimo_intento_en_ambos_casos(self):
        def cuerpo_del_intento_numero(email, n):
            for _ in range(n - 1):
                self.login(email, "mala")
            return self.login(email, "mala").json()

        real = cuerpo_del_intento_numero(self.REGISTRADO, 4)
        falso = cuerpo_del_intento_numero(self.INEXISTENTE, 4)
        self.assertIn("aviso", real)
        self.assertEqual(real, falso)
        # El aviso no cuantifica nada: solo anuncia que el proximo fallo bloquea.
        self.assertNotIn("4", real["aviso"])

    def test_bloqueo_tambien_para_correo_inexistente(self):
        for _ in range(4):
            self.assertEqual(self.login(self.INEXISTENTE, "mala").status_code, 401)
        bloqueado = self.login(self.INEXISTENTE, "mala")
        self.assertEqual(bloqueado.status_code, 423)
        self.assertEqual(bloqueado.json()["codigo"], "CUENTA_BLOQUEADA")
        self.assertIsNotNone(bloqueado.json()["desbloqueo_en"])

    def test_bloqueo_indistinguible_entre_correo_real_e_inexistente(self):
        for _ in range(5):
            real = self.login(self.REGISTRADO, "mala")
            falso = self.login(self.INEXISTENTE, "mala")
        self.assertEqual(real.status_code, 423)
        self.assertEqual(real.status_code, falso.status_code)
        self.assertEqual(set(real.json()), set(falso.json()))

    def test_sin_diferencia_de_tiempo_notable_entre_los_dos_casos(self):
        """Ambos caminos calculan el hash de la contrasena (el backend de
        Django lo hace en vacio cuando el usuario no existe), asi que el
        tiempo de respuesta no delata si el correo esta registrado."""
        def mejor_tiempo(email):
            medidas = []
            for _ in range(3):
                self.reiniciar_intentos()
                cache.clear()
                inicio = time.perf_counter()
                self.login(email, "contrasena-mala")
                medidas.append(time.perf_counter() - inicio)
            return min(medidas)

        real = mejor_tiempo(self.REGISTRADO)
        falso = mejor_tiempo(self.INEXISTENTE)
        # Tolerancia amplia a proposito: lo que se vigila es que no quede una
        # diferencia de ORDEN DE MAGNITUD (la que dejaba el retorno temprano
        # sin verificar contrasena), no el ruido de una maquina cargada.
        self.assertLess(abs(real - falso), 0.5 * max(real, falso),
                        "real=%.3fs inexistente=%.3fs" % (real, falso))


# ============ BUG-05: coste del login exitoso (techo de consultas) ===========

class CosteLoginTest(BaseCuentasTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta(email="rapido@test.co")

    def test_login_exitoso_no_supera_el_techo_de_consultas(self):
        # 1 resolver usuario+perfil+empresa+rol / 1 authenticate / 1 UPDATE de
        # last_login / 1 insert de auditoria. Sin select_related el contexto
        # costaba 3 consultas extra.
        with self.assertNumQueries(4):
            respuesta = self.login("rapido@test.co", "Clave12345")
        self.assertEqual(respuesta.status_code, 200)

    def test_me_no_supera_el_techo_de_consultas(self):
        token = self.login("rapido@test.co", "Clave12345").json()["access"]
        cabecera = "Bearer " + token
        with self.assertNumQueries(3):  # usuario del token / perfil / permisos
            respuesta = self.client.get(reverse("auth-me"),
                                        HTTP_AUTHORIZATION=cabecera)
        self.assertEqual(respuesta.status_code, 200)


# ================ BUG-18: DEBUG=False no publica el URLconf ==================

class ErroresSinDetalleInternoTest(TestCase):
    def test_404_con_debug_false_devuelve_json_sin_urlconf(self):
        with override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"]):
            respuesta = self.client.get("/api/ruta-inexistente/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        cuerpo = respuesta.content.decode()
        self.assertNotIn("URLconf", cuerpo)
        self.assertNotIn("urlpatterns", cuerpo)
        self.assertEqual(respuesta.json()["codigo"], "NO_ENCONTRADO")


# ====== BUG-13: los conteos de Roles y Usuarios miran la MISMA empresa ======

class ConteoRolesPorEmpresaTest(TestCase):
    """Roles decia 5 usuarios y Usuarios mostraba 2 sobre la misma empresa.

    Quien estaba mal era Roles: los roles base son GLOBALES (empresa=None), asi
    que `Count("perfiles")` sin filtro sumaba los perfiles de todos los
    tenants. Usuarios ya filtraba por empresa y era el correcto.
    """

    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")
        cls.empresa_a = Empresa.objects.create(nombre="Empresa A", nit="900100100")
        cls.empresa_b = Empresa.objects.create(nombre="Empresa B", nit="900200200")
        cls.admin_a = cls.crear(cls.empresa_a, "admin-a@test.co", "ADMINISTRADOR")
        cls.admin_b = cls.crear(cls.empresa_b, "admin-b@test.co", "ADMINISTRADOR")
        # A: 1 admin + 1 empleado. B: 1 admin + 3 empleados.
        cls.crear(cls.empresa_a, "emp-a1@test.co", "EMPLEADO")
        for n in range(3):
            cls.crear(cls.empresa_b, "emp-b%d@test.co" % n, "EMPLEADO")

    @classmethod
    def crear(cls, empresa, email, rol, activo=True):
        usuario = User.objects.create_user(username=email, email=email,
                                           password="Clave12345", first_name=email)
        if not activo:
            usuario.is_active = False
            usuario.save(update_fields=["is_active"])
        return Perfil.objects.create(usuario=usuario, empresa=empresa,
                                     rol=Rol.de_nombre(rol))

    def cliente_de(self, perfil):
        cliente = APIClient()
        cliente.force_authenticate(user=perfil.usuario)
        return cliente

    def conteos_de_roles(self, perfil):
        respuesta = self.cliente_de(perfil).get("/api/seguridad/roles/")
        self.assertEqual(respuesta.status_code, 200)
        return {r["nombre"]: r["total_usuarios_activos"]
                for r in respuesta.json()["resultados"]}

    def test_roles_cuenta_solo_usuarios_de_mi_empresa(self):
        self.assertEqual(self.conteos_de_roles(self.admin_a),
                         {"ADMINISTRADOR": 1, "EMPLEADO": 1, "CLIENTE": 0})
        self.assertEqual(self.conteos_de_roles(self.admin_b),
                         {"ADMINISTRADOR": 1, "EMPLEADO": 3, "CLIENTE": 0})

    def test_roles_y_usuarios_dan_el_mismo_total(self):
        for perfil in (self.admin_a, self.admin_b):
            cliente = self.cliente_de(perfil)
            usuarios = cliente.get("/api/seguridad/usuarios/").json()["resultados"]
            activos = [u for u in usuarios if u["activo"]]
            total_roles = sum(self.conteos_de_roles(perfil).values())
            self.assertEqual(total_roles, len(activos),
                             "Roles y Usuarios discrepan en %s" % perfil.empresa.nombre)

    def test_usuarios_no_oculta_cuentas_reales_de_la_empresa(self):
        """La lista de Usuarios trae TODAS las cuentas de la empresa,
        incluidas las desactivadas (con activo=False); lo unico que oculta
        son los perfiles borrados logicamente."""
        self.crear(self.empresa_a, "desactivado-a@test.co", "EMPLEADO", activo=False)
        borrado = self.crear(self.empresa_a, "borrado-a@test.co", "EMPLEADO")
        Perfil.objects.filter(pk=borrado.pk).update(deleted_at=timezone.now())

        correos = {u["email"] for u in self.cliente_de(self.admin_a)
                   .get("/api/seguridad/usuarios/").json()["resultados"]}
        esperados = {p.usuario.email for p in
                     Perfil.objects.filter(empresa=self.empresa_a,
                                           deleted_at__isnull=True)}
        self.assertEqual(correos, esperados)
        self.assertIn("desactivado-a@test.co", correos)
        self.assertNotIn("borrado-a@test.co", correos)

    def test_borrar_rol_no_revela_el_uso_que_le_da_otra_empresa(self):
        """El bloqueo ROL_CON_USUARIOS_ACTIVOS contaba perfiles de todos los
        tenants y su mensaje publicaba cuantos eran. Ahora el conteo solo mira
        mi empresa; si aun asi queda un perfil ajeno (estado que la API no
        permite crear), el borrado falla con 400 generico, no con un 500."""
        rol_a = Rol.objects.create(nombre="AUDITOR", empresa=self.empresa_a)
        ajeno = self.crear(self.empresa_b, "ajeno@test.co", "EMPLEADO")
        Perfil.objects.filter(pk=ajeno.pk).update(rol=rol_a)

        respuesta = self.cliente_de(self.admin_a).delete(
            "/api/seguridad/roles/%s/" % rol_a.id)
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "ROL_EN_USO")
        self.assertNotIn("usuarios_activos", respuesta.json())

    def test_borrar_rol_propio_sin_usuarios_funciona(self):
        rol_a = Rol.objects.create(nombre="REVISOR", empresa=self.empresa_a)
        respuesta = self.cliente_de(self.admin_a).delete(
            "/api/seguridad/roles/%s/" % rol_a.id)
        self.assertEqual(respuesta.status_code, 204)

    def test_cliente_es_el_rol_sin_permisos_del_marketplace(self):
        """CLIENTE con 0 permisos es intencional: el comprador del
        marketplace no usa la tabla de permisos (ver `EsPersonal`, que exige
        rol de personal o al menos un permiso)."""
        cliente = Rol.de_nombre("CLIENTE")
        self.assertEqual(RolPermiso.objects.filter(rol=cliente).count(), 0)
        perfil = self.crear(self.empresa_a, "comprador@test.co", "CLIENTE")
        self.assertFalse(EsPersonal().has_permission(
            SimpleNamespace(user=perfil.usuario), None))


# ===== BUG-09 (fase 2.1): la identidad no distingue mayusculas ==============

class CorreoSinMayusculasTest(BaseCuentasTest):
    """La unicidad y la resolucion de identidad tienen que ignorar mayusculas
    sin depender de la collation de la base: con `utf8mb4_bin` (o en otro
    motor) un UNIQUE plano dejaria convivir Ana@x.co y ana@x.co y reabriria
    el BUG-09."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta(email="ana@elprogreso.co",
                                                rol="ADMINISTRADOR")

    def test_login_funciona_con_el_correo_en_otra_caja(self):
        respuesta = self.login("ANA@ElProgreso.co", "Clave12345")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["usuario"]["id"], str(self.user.id))

    def test_indice_unico_rechaza_el_mismo_correo_en_otra_caja(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username="otra@elprogreso.co",
                                         email="Ana@ElProgreso.co",
                                         password="Clave12345")

    def test_indice_unico_rechaza_el_mismo_username_en_otra_caja(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username="ANA@elprogreso.co",
                                         email="distinto@elprogreso.co",
                                         password="Clave12345")

    def test_api_rechaza_crear_usuario_que_solo_cambia_mayusculas(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.user)
        respuesta = cliente.post("/api/seguridad/usuarios/", {
            "nombre": "Ana Dos", "email": "ANA@ElProgreso.co",
            "password": "Clave12345", "rol": "EMPLEADO"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "DATOS_INVALIDOS")
        self.assertIn("email", respuesta.json()["errores"])

    def test_api_guarda_el_correo_normalizado(self):
        cliente = APIClient()
        cliente.force_authenticate(user=self.user)
        respuesta = cliente.post("/api/seguridad/usuarios/", {
            "nombre": "Beto Nuevo", "email": "  BETO@ElProgreso.CO  ",
            "password": "Clave12345", "rol": "EMPLEADO"}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        creado = User.objects.get(email="beto@elprogreso.co")
        self.assertEqual(creado.username, "beto@elprogreso.co")

    def test_email_disponible_ignora_mayusculas(self):
        tomado = self.client.get(reverse("auth-email-disponible"),
                                 {"email": "ANA@ElProgreso.co"})
        self.assertFalse(tomado.json()["disponible"])

    def test_recuperacion_encuentra_la_cuenta_en_otra_caja(self):
        mail.outbox.clear()
        respuesta = self.client.post(reverse("auth-password-reset"),
                                     {"email": "ANA@ElProgreso.co"},
                                     content_type="application/json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)


class VerificacionIdentidadesDuplicadasTest(TransactionTestCase):
    """El chequeo previo a la migracion agrupa por LOWER(), no por la
    comparacion nativa de la base.

    Para poder insertar el duplicado hay que soltar antes los indices unicos:
    una vez aplicada la migracion 0012 la base ya no los admite. Lo que se
    prueba aqui es el DIAGNOSTICO -- que la migracion sepa explicar una base
    heredada sucia en vez de fallar con un `Duplicate entry` a secas.
    """

    INDICES = [
        ("username", "ALTER TABLE `auth_user` ADD UNIQUE KEY `username` (`username`)"),
        ("uniq_auth_user_email_lower",
         "ALTER TABLE `auth_user` ADD UNIQUE KEY `uniq_auth_user_email_lower` "
         "((LOWER(`email`)))"),
        ("uniq_auth_user_username_lower",
         "ALTER TABLE `auth_user` ADD UNIQUE KEY `uniq_auth_user_username_lower` "
         "((LOWER(`username`)))"),
    ]

    def setUp(self):
        self.soltados = []
        with connection.cursor() as cursor:
            for nombre, recrear in self.INDICES:
                if self._existe(cursor, nombre):
                    cursor.execute(f"ALTER TABLE `auth_user` DROP KEY `{nombre}`")
                    self.soltados.append(recrear)

    def tearDown(self):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_user")
            for recrear in self.soltados:
                cursor.execute(recrear)

    @staticmethod
    def _existe(cursor, nombre):
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'auth_user' "
            "AND index_name = %s", [nombre])
        return cursor.fetchone()[0] > 0

    @staticmethod
    def _insertar(cursor, username, email):
        cursor.execute(
            "INSERT INTO auth_user (password, is_superuser, username, "
            "first_name, last_name, email, is_staff, is_active, date_joined) "
            "VALUES ('x', 0, %s, '', '', %s, 0, 1, NOW())", [username, email])

    def test_detecta_duplicado_por_correo_ignorando_mayusculas(self):
        with connection.cursor() as cursor:
            self._insertar(cursor, "u1", "dup@test.co")
            self._insertar(cursor, "u2", "DUP@test.co")
            hallazgos = buscar(cursor)
        self.assertIn("email", hallazgos)
        self.assertEqual(hallazgos["email"][0][0], "dup@test.co")
        self.assertEqual(hallazgos["email"][0][1], 2)

    def test_detecta_duplicado_por_username_ignorando_mayusculas(self):
        with connection.cursor() as cursor:
            self._insertar(cursor, "pepe", "pepe@test.co")
            self._insertar(cursor, "PEPE", "otro@test.co")
            hallazgos = buscar(cursor)
        self.assertIn("username", hallazgos)
        self.assertEqual(hallazgos["username"][0][0], "pepe")

    def test_correo_vacio_no_cuenta_como_duplicado(self):
        """Django permite `email=''` (createsuperuser sin correo): esas filas
        no identifican a nadie y no deben bloquear la migracion."""
        with connection.cursor() as cursor:
            self._insertar(cursor, "s1", "")
            self._insertar(cursor, "s2", "")
            hallazgos = buscar(cursor)
        self.assertNotIn("email", hallazgos)

    def test_sin_duplicados_no_hay_hallazgos(self):
        with connection.cursor() as cursor:
            self._insertar(cursor, "a@test.co", "a@test.co")
            self._insertar(cursor, "b@test.co", "b@test.co")
            self.assertEqual(buscar(cursor), {})

    def test_comando_falla_y_dice_que_arreglar(self):
        with connection.cursor() as cursor:
            self._insertar(cursor, "z1", "z@test.co")
            self._insertar(cursor, "z2", "Z@test.co")
        with self.assertRaises(CommandError):
            call_command("verificar_emails_duplicados")

    def test_descripcion_nombra_columna_valor_e_ids(self):
        texto = describir({"email": [("dup@test.co", 2, "7,9")]})
        self.assertIn("email", texto)
        self.assertIn("dup@test.co", texto)
        self.assertIn("7,9", texto)


# ===== BUG-19 (fase 2.1): el bloqueo no depende de la IP del atacante ======

class BloqueoIndependienteDeIPTest(BaseCuentasTest):
    """Con la IP en la clave del contador anonimo quedaba un oraculo: el
    bloqueo de una cuenta real es global, asi que cinco intentos repartidos
    entre cinco IPs devolvian 423 para un correo registrado y seguian
    devolviendo 401 para uno inexistente."""

    REGISTRADO = "existe@test.co"
    INEXISTENTE = "no-existe@test.co"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta(email=cls.REGISTRADO)

    def setUp(self):
        cache.clear()
        Perfil.objects.filter(pk=self.perfil.pk).update(intentos_fallidos=0,
                                                        fecha_desbloqueo=None)

    def secuencia_desde_ips_distintas(self, email):
        """Un intento por IP, tantas IPs como el maximo de intentos."""
        codigos = []
        for n in range(1, 6):
            respuesta = self.client.post(
                reverse("auth-login"),
                {"email": email, "password": "mala"},
                content_type="application/json",
                REMOTE_ADDR=f"203.0.113.{n}")
            codigos.append(respuesta.status_code)
        return codigos

    def test_misma_secuencia_para_correo_real_e_inexistente(self):
        real = self.secuencia_desde_ips_distintas(self.REGISTRADO)
        cache.clear()
        falso = self.secuencia_desde_ips_distintas(self.INEXISTENTE)
        self.assertEqual(real, [401, 401, 401, 401, 423])
        self.assertEqual(real, falso)

    def test_el_correo_inexistente_tambien_se_bloquea_cambiando_de_ip(self):
        self.secuencia_desde_ips_distintas(self.INEXISTENTE)
        # Una IP nueva no reinicia el contador: el bloqueo va por identidad.
        respuesta = self.client.post(
            reverse("auth-login"),
            {"email": self.INEXISTENTE, "password": "mala"},
            content_type="application/json", REMOTE_ADDR="198.51.100.77")
        self.assertEqual(respuesta.status_code, 423)

    def test_el_login_sigue_en_pie_si_el_cache_falla(self):
        """La tabla de DatabaseCache puede no existir todavia: un fallo de
        cache no puede convertir el login en un 500."""
        from unittest import mock

        with mock.patch("cuentas.intentos.cache") as cache_roto:
            cache_roto.get.side_effect = Exception("cache caido")
            cache_roto.set.side_effect = Exception("cache caido")
            respuesta = self.login(self.INEXISTENTE, "mala")
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["codigo"], "CREDENCIALES_INVALIDAS")


REST_FRAMEWORK_LOGIN_ESTRECHO = {
    **settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
                               "auth_login": "3/minute"},
}


@override_settings(REST_FRAMEWORK=REST_FRAMEWORK_LOGIN_ESTRECHO)
class ThrottlingDeLoginTest(BaseCuentasTest):
    """Cada intento cuesta un hash PBKDF2 (~650 ms): sin limite por IP el
    login es un vector de denegacion de servicio. El limite acota el gasto
    por IP y NO bloquea cuentas."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta(email="dos@test.co")

    def setUp(self):
        cache.clear()

    def test_se_corta_por_ip_antes_de_gastar_mas_hashes(self):
        for _ in range(3):
            self.assertEqual(self.login("dos@test.co", "mala").status_code, 401)
        cortado = self.login("dos@test.co", "mala")
        self.assertEqual(cortado.status_code, 429)

    def test_el_limite_es_por_ip_y_no_bloquea_la_cuenta(self):
        for _ in range(4):
            self.client.post(reverse("auth-login"),
                             {"email": "dos@test.co", "password": "mala"},
                             content_type="application/json",
                             REMOTE_ADDR="203.0.113.9")
        # Otra IP sigue pudiendo entrar: el 429 no toco la cuenta.
        respuesta = self.client.post(reverse("auth-login"),
                                     {"email": "dos@test.co", "password": "Clave12345"},
                                     content_type="application/json",
                                     REMOTE_ADDR="198.51.100.5")
        self.assertEqual(respuesta.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.intentos_fallidos, 0)


# ===== BUG-13 (fase 2.1): los roles globales son de solo lectura ============

class RolesGlobalesSoloLecturaTest(TestCase):
    """Los roles con `empresa=None` los comparten TODOS los tenants: si el
    administrador de una empresa pudiera tocarlos, estaria cambiando la
    autorizacion de la plataforma entera.

    La guarda anterior comparaba el nombre contra ROLES_DEL_SISTEMA, asi que
    un rol global con cualquier otro nombre quedaba editable por cualquier
    empresa.
    """

    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")
        cls.empresa_a = Empresa.objects.create(nombre="Empresa A", nit="900110110")
        cls.empresa_b = Empresa.objects.create(nombre="Empresa B", nit="900220220")
        cls.admin_a = cls.crear(cls.empresa_a, "jefe-a@test.co")
        cls.admin_b = cls.crear(cls.empresa_b, "jefe-b@test.co")
        # Rol GLOBAL con un nombre que no esta en ROLES_DEL_SISTEMA: es el caso
        # que se colaba por la guarda vieja.
        cls.rol_global = Rol.objects.create(nombre="SOPORTE_PLATAFORMA",
                                            empresa=None)
        cls.rol_propio_b = Rol.objects.create(nombre="AUDITOR_B",
                                              empresa=cls.empresa_b)

    @classmethod
    def crear(cls, empresa, email):
        usuario = User.objects.create_user(username=email, email=email,
                                           password="Clave12345", first_name=email)
        return Perfil.objects.create(usuario=usuario, empresa=empresa,
                                     rol=Rol.de_nombre("ADMINISTRADOR"))

    def cliente_de(self, perfil):
        cliente = APIClient()
        cliente.force_authenticate(user=perfil.usuario)
        return cliente

    def ruta(self, rol):
        return "/api/seguridad/roles/%s/" % rol.id

    # ---------------------------- roles globales ----------------------------

    def test_no_puede_renombrar_un_rol_base(self):
        rol = Rol.de_nombre("EMPLEADO")
        respuesta = self.cliente_de(self.admin_a).patch(
            self.ruta(rol), {"nombre": "MIO"}, format="json")
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["codigo"], "ROL_DEL_SISTEMA")
        rol.refresh_from_db()
        self.assertEqual(rol.nombre, "EMPLEADO")

    def test_no_puede_cambiar_los_permisos_de_un_rol_base(self):
        rol = Rol.de_nombre("EMPLEADO")
        antes = set(RolPermiso.objects.filter(rol=rol)
                    .values_list("permiso__codigo", flat=True))
        respuesta = self.cliente_de(self.admin_a).patch(
            self.ruta(rol), {"permisos": ["usuarios.gestionar"]}, format="json")
        self.assertEqual(respuesta.status_code, 403)
        despues = set(RolPermiso.objects.filter(rol=rol)
                      .values_list("permiso__codigo", flat=True))
        self.assertEqual(antes, despues)

    def test_no_puede_eliminar_un_rol_base(self):
        rol = Rol.de_nombre("CLIENTE")
        respuesta = self.cliente_de(self.admin_a).delete(self.ruta(rol))
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["codigo"], "ROL_DEL_SISTEMA")
        self.assertTrue(Rol.objects.filter(pk=rol.pk).exists())

    def test_un_rol_global_con_otro_nombre_tambien_esta_protegido(self):
        """El agujero concreto: la guarda vieja solo miraba el nombre."""
        for peticion in (
            lambda c: c.patch(self.ruta(self.rol_global),
                              {"nombre": "SECUESTRADO"}, format="json"),
            lambda c: c.patch(self.ruta(self.rol_global),
                              {"permisos": ["usuarios.gestionar"]}, format="json"),
            lambda c: c.delete(self.ruta(self.rol_global)),
        ):
            respuesta = peticion(self.cliente_de(self.admin_a))
            self.assertEqual(respuesta.status_code, 403)
            self.assertEqual(respuesta.json()["codigo"], "ROL_DEL_SISTEMA")
        self.rol_global.refresh_from_db()
        self.assertEqual(self.rol_global.nombre, "SOPORTE_PLATAFORMA")
        self.assertEqual(RolPermiso.objects.filter(rol=self.rol_global).count(), 0)

    def test_los_globales_se_marcan_es_sistema_y_se_pueden_leer_y_clonar(self):
        cliente = self.cliente_de(self.admin_a)
        listado = cliente.get("/api/seguridad/roles/").json()["resultados"]
        globales = {r["nombre"] for r in listado if r["es_sistema"]}
        self.assertEqual(globales, {"ADMINISTRADOR", "EMPLEADO", "CLIENTE",
                                    "SOPORTE_PLATAFORMA"})

        # La via para personalizar uno es clonarlo: la copia es propia.
        clon = cliente.post("/api/seguridad/roles/%s/clonar/" % self.rol_global.id)
        self.assertEqual(clon.status_code, 201)
        self.assertFalse(clon.json()["es_sistema"])
        self.assertEqual(Rol.objects.get(pk=clon.json()["id"]).empresa_id,
                         self.empresa_a.id)

    # ------------------------- aislamiento entre tenants --------------------

    def test_el_admin_de_a_no_ve_los_roles_propios_de_b(self):
        listado = self.cliente_de(self.admin_a).get(
            "/api/seguridad/roles/").json()["resultados"]
        self.assertNotIn("AUDITOR_B", {r["nombre"] for r in listado})

    def test_el_admin_de_a_no_puede_tocar_un_rol_de_b(self):
        cliente = self.cliente_de(self.admin_a)
        ruta = self.ruta(self.rol_propio_b)
        self.assertEqual(cliente.get(ruta).status_code, 404)
        self.assertEqual(cliente.patch(ruta, {"nombre": "ROBADO"},
                                       format="json").status_code, 404)
        self.assertEqual(cliente.delete(ruta).status_code, 404)
        self.rol_propio_b.refresh_from_db()
        self.assertEqual(self.rol_propio_b.nombre, "AUDITOR_B")

    def test_cada_empresa_edita_sus_propios_roles(self):
        respuesta = self.cliente_de(self.admin_b).patch(
            self.ruta(self.rol_propio_b), {"nombre": "AUDITOR_INTERNO"},
            format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.rol_propio_b.refresh_from_db()
        self.assertEqual(self.rol_propio_b.nombre, "AUDITOR_INTERNO")


# ===== BUG-27: "ultimo acceso" salia vacio en todas las filas ===============

class UltimoAccesoTest(BaseCuentasTest):
    """`authenticate()` no toca `last_login`: eso lo hace el receptor de la
    senal `user_logged_in`, que solo dispara `django.contrib.auth.login()`, y
    esta API es por JWT. Sin escribirlo a mano, `last_login` se quedaba en NULL
    para siempre y las columnas "ultimo acceso" de /admin/usuarios y de
    Empleados salian vacias."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_roles")
        cls.user, cls.perfil = cls.crear_cuenta(email="acceso@test.co",
                                                rol="ADMINISTRADOR")

    def test_el_login_exitoso_registra_el_ultimo_acceso(self):
        self.assertIsNone(self.user.last_login)
        antes = timezone.now()
        self.assertEqual(self.login("acceso@test.co", "Clave12345").status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)
        self.assertGreaterEqual(self.user.last_login, antes)

    def test_el_login_fallido_no_lo_toca(self):
        self.login("acceso@test.co", "mala")
        self.user.refresh_from_db()
        self.assertIsNone(self.user.last_login)

    def test_la_api_de_usuarios_lo_expone(self):
        self.login("acceso@test.co", "Clave12345")
        cliente = APIClient()
        cliente.force_authenticate(user=self.user)
        fila = next(u for u in cliente.get("/api/seguridad/usuarios/")
                    .json()["resultados"] if u["email"] == "acceso@test.co")
        self.assertIsNotNone(fila["ultimo_login"])
