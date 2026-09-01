import hashlib
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class Rol(models.Model):
    """Rol de una empresa. Cada empresa tiene sus propios roles; los roles
    base ADMINISTRADOR, EMPLEADO y CLIENTE se crean automaticamente al crear
    la empresa, y la empresa puede crear los suyos y ajustar permisos."""

    ROLES_BASE = ["ADMINISTRADOR", "EMPLEADO", "CLIENTE"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.CASCADE, related_name="roles")
    nombre = models.CharField(max_length=30)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "rol"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "nombre"], name="rol_empresa_nombre_unico"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.empresa_id})"

    @property
    def es_sistema(self) -> bool:
        return self.nombre in self.ROLES_BASE

    @classmethod
    def de_nombre(cls, empresa, nombre: str) -> "Rol":
        """Obtiene o crea un rol por nombre dentro de la empresa."""
        rol, _ = cls.objects.get_or_create(empresa=empresa, nombre=nombre)
        return rol


class Permiso(models.Model):
    """Accion puntual del sistema, p. ej. 'ventas.gestionar'."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "permiso"
        ordering = ["codigo"]

    def __str__(self):
        return self.codigo


class RolPermiso(models.Model):
    """Asignacion de permisos a cada rol (N:M con tabla intermedia)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name="rol_permisos")
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, related_name="rol_permisos")

    class Meta:
        db_table = "rol_permiso"
        unique_together = ("rol", "permiso")

    def __str__(self):
        return f"{self.rol.nombre}: {self.permiso.codigo}"


class Perfil(models.Model):
    ROLES = [("ADMINISTRADOR", "Administrador"), ("EMPLEADO", "Empleado"),
             ("CLIENTE", "Cliente")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="perfil")
    empresa = models.ForeignKey("core.Empresa", on_delete=models.PROTECT, related_name="perfiles")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="perfiles")
    es_propietario = models.BooleanField(default=False)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    fecha_desbloqueo = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "perfil"
        verbose_name_plural = "Perfiles"

    def __str__(self):
        return f"{self.usuario.email} ({self.rol.nombre})"

    @property
    def nombre_rol(self) -> str:
        return self.rol.nombre

    def tiene_permiso(self, codigo: str) -> bool:
        return RolPermiso.objects.filter(rol=self.rol, permiso__codigo=codigo).exists()

    def esta_bloqueado(self) -> bool:
        return bool(self.fecha_desbloqueo and self.fecha_desbloqueo > timezone.now())

    def bloquear_cuenta(self) -> None:
        minutos = getattr(settings, "MINUTOS_BLOQUEO", 15)
        self.fecha_desbloqueo = timezone.now() + timedelta(minutes=minutos)

    def registrar_intento_fallido(self) -> None:
        maximo = getattr(settings, "MAX_INTENTOS_LOGIN", 5)
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= maximo:
            self.bloquear_cuenta()
        self.save(update_fields=["intentos_fallidos", "fecha_desbloqueo"])

    def intentos_restantes(self) -> int:
        maximo = getattr(settings, "MAX_INTENTOS_LOGIN", 5)
        return max(0, maximo - self.intentos_fallidos)

    def reiniciar_intentos(self) -> None:
        if self.intentos_fallidos or self.fecha_desbloqueo:
            self.intentos_fallidos = 0
            self.fecha_desbloqueo = None
            self.save(update_fields=["intentos_fallidos", "fecha_desbloqueo"])


class ActividadUsuario(models.Model):
    """Auditoria automatica: registra cada accion de escritura del sistema.
    `usuario` puede ser nulo para eventos de cuentas inexistentes (p. ej.
    intentos de login con correos desconocidos)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="actividades")
    accion = models.CharField(max_length=120)
    detalle = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "actividad_usuario"
        ordering = ["-fecha"]
        verbose_name_plural = "Actividades de usuarios"

    def __str__(self):
        actor = self.usuario.email if self.usuario else "anonimo"
        return f"{actor} - {self.accion}"

    @classmethod
    def registrar(cls, usuario=None, accion: str = "", detalle: str = "") -> None:
        cls.objects.create(usuario=usuario, accion=accion[:120], detalle=detalle[:255])


PERMISOS_BASE = [
    ("usuarios.gestionar", "Crear, editar y desactivar cuentas de la empresa"),
    ("roles.asignar", "Asignar roles y permisos a los usuarios"),
    ("productos.gestionar", "Crear, editar y desactivar productos"),
    ("inventario.movimientos", "Registrar entradas, salidas y ajustes de stock"),
    ("clientes.gestionar", "Administrar el directorio de clientes"),
    ("ventas.gestionar", "Registrar, completar y anular ventas"),
    ("reportes.ver", "Consultar reportes e indicadores"),
    ("configuracion.gestionar", "Editar los datos de la empresa"),
]

PERMISOS_POR_ROL = {
    "ADMINISTRADOR": [codigo for codigo, _ in PERMISOS_BASE],
    "EMPLEADO": ["productos.gestionar", "inventario.movimientos", "clientes.gestionar",
                 "ventas.gestionar", "reportes.ver"],
    "CLIENTE": [],
}


def crear_roles_base(empresa) -> None:
    """Crea (idempotente) los roles base ADMINISTRADOR, EMPLEADO y CLIENTE
    para una empresa, con sus permisos por defecto."""
    permisos = {}
    for codigo, descripcion in PERMISOS_BASE:
        permisos[codigo], _ = Permiso.objects.get_or_create(
            codigo=codigo, defaults={"descripcion": descripcion})
    for nombre, codigos in PERMISOS_POR_ROL.items():
        rol, _ = Rol.objects.get_or_create(empresa=empresa, nombre=nombre)
        for codigo in codigos:
            RolPermiso.objects.get_or_create(rol=rol, permiso=permisos[codigo])


class TokenRecuperacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name="tokens_recuperacion")
    token_hash = models.CharField(max_length=64, db_index=True)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField()
    usado = models.BooleanField(default=False)

    class Meta:
        db_table = "token_recuperacion"

    @staticmethod
    def calcular_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def emitir(cls, perfil: "Perfil", minutos: int = 30) -> str:
        cls.objects.filter(perfil=perfil, usado=False).update(usado=True)
        token = get_random_string(48)
        cls.objects.create(
            perfil=perfil, token_hash=cls.calcular_hash(token),
            expira=timezone.now() + timedelta(minutes=minutos),
        )
        return token

    def es_valido(self) -> bool:
        return not self.usado and self.expira > timezone.now()
