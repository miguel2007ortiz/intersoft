"""Conteo de intentos fallidos de login.

Por que existe este modulo
--------------------------
El login tiene que contar intentos fallidos ANTES de saber si el correo
corresponde a una cuenta real. Antes se resolvia un `Perfil` por correo
(`Perfil.objects.filter(usuario__email__iexact=email).first()`) y se cargaban
los fallos sobre ese perfil: con dos perfiles que compartieran correo, los
intentos se anotaban en un perfil elegido de forma ambigua (el primero que
devolviera MySQL) y podian bloquear una cuenta distinta de la que se estaba
intentando abrir.

Clave de conteo elegida
-----------------------
1. Si el correo resuelve a un `User` -- y resuelve a uno solo, porque
   `auth_user.email` tiene indice UNIQUE (migracion 0005 + verificacion en
   0010) -- la clave es el `Perfil` de ESE usuario. Es persistente, sobrevive
   a un cambio de IP del atacante y coincide con la semantica del bloqueo de
   cuenta que ya expone la API (`fecha_desbloqueo`).
2. Si el correo no existe no hay cuenta que bloquear, asi que la clave es
   `correo normalizado + IP del cliente`, guardada en cache con la misma
   ventana de bloqueo. Esto da al atacante exactamente la misma secuencia de
   401 y 423 que con un correo real (requisito anti-enumeracion), sin crear
   cuentas fantasma en la base de datos y sin dejar los correos inexistentes
   como un canal de fuerza bruta sin limite. El correo se guarda hasheado
   para no dejar direcciones en claro en el cache.

Ambas estrategias implementan la misma interfaz para que la vista de login no
tenga que ramificar segun exista o no la cuenta (de esa ramificacion salian
las diferencias de cuerpo y de tiempo que permitian enumerar correos).
"""

import hashlib
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def maximo_intentos() -> int:
    return getattr(settings, "MAX_INTENTOS_LOGIN", 5)


def minutos_bloqueo() -> int:
    return getattr(settings, "MINUTOS_BLOQUEO", 15)


def ip_cliente(request) -> str:
    """IP real del cliente. Detras de nginx la de confianza es la ULTIMA de
    X-Forwarded-For (el proxy anade la del cliente al final); mismo criterio
    que `core.throttling.IPScopedRateThrottle`."""
    reenviadas = request.META.get("HTTP_X_FORWARDED_FOR")
    if reenviadas:
        partes = [p.strip() for p in reenviadas.split(",") if p.strip()]
        if partes:
            return partes[-1]
    return request.META.get("REMOTE_ADDR", "")


class ContadorPerfil:
    """Cuenta sobre el `Perfil` del usuario resuelto de forma deterministica."""

    def __init__(self, perfil):
        self.perfil = perfil

    def esta_bloqueado(self) -> bool:
        return self.perfil.esta_bloqueado()

    @property
    def desbloqueo_en(self):
        return self.perfil.fecha_desbloqueo

    def registrar_fallo(self) -> None:
        self.perfil.registrar_intento_fallido()

    def intentos_restantes(self) -> int:
        return self.perfil.intentos_restantes()

    def reiniciar(self) -> None:
        self.perfil.reiniciar_intentos()


class ContadorAnonimo:
    """Cuenta en cache por (correo normalizado, IP) cuando el correo no existe.

    Replica la ventana y el maximo del contador de perfil para que la
    respuesta sea indistinguible de la de una cuenta real.
    """

    PREFIJO = "login:intentos:"

    def __init__(self, email: str, ip: str):
        huella = hashlib.sha256(f"{email.strip().lower()}|{ip}".encode()).hexdigest()
        self.clave = f"{self.PREFIJO}{huella}"
        self._estado = cache.get(self.clave) or {"fallos": 0, "desbloqueo_en": None}

    # La entrada vive lo suficiente para cubrir la ventana de bloqueo entera.
    def _ttl(self) -> int:
        return minutos_bloqueo() * 60

    def esta_bloqueado(self) -> bool:
        desbloqueo = self._estado.get("desbloqueo_en")
        return bool(desbloqueo and desbloqueo > timezone.now())

    @property
    def desbloqueo_en(self):
        return self._estado.get("desbloqueo_en")

    def registrar_fallo(self) -> None:
        self._estado["fallos"] = self._estado.get("fallos", 0) + 1
        if self._estado["fallos"] >= maximo_intentos():
            self._estado["desbloqueo_en"] = (
                timezone.now() + timedelta(minutes=minutos_bloqueo()))
        cache.set(self.clave, self._estado, self._ttl())

    def intentos_restantes(self) -> int:
        return max(0, maximo_intentos() - self._estado.get("fallos", 0))

    def reiniciar(self) -> None:
        cache.delete(self.clave)


def contador_para(usuario, email: str, request):
    """Devuelve el contador que corresponde a este intento de login.

    `usuario` es el resultado de resolver el correo contra `auth_user`; si es
    None (o no tiene perfil) se cae al contador anonimo por correo + IP.
    """
    perfil = getattr(usuario, "perfil", None) if usuario is not None else None
    if perfil is not None:
        return ContadorPerfil(perfil)
    return ContadorAnonimo(email, ip_cliente(request))
