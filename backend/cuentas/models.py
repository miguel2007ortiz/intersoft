import hashlib
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class Perfil(models.Model):
    ROLES = [("ADMINISTRADOR", "Administrador"), ("EMPLEADO", "Empleado"),
             ("CLIENTE", "Cliente")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="perfil")
    empresa = models.ForeignKey("core.Empresa", on_delete=models.PROTECT, related_name="perfiles")
    rol = models.CharField(max_length=20, choices=ROLES, default="EMPLEADO")
    es_propietario = models.BooleanField(default=False)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    fecha_desbloqueo = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "perfil"
        verbose_name_plural = "Perfiles"

    def __str__(self):
        return f"{self.usuario.email} ({self.rol})"

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
