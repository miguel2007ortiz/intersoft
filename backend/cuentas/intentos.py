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
   `LOWER(auth_user.email)` tiene indice UNIQUE (migracion 0012, que ademas
   verifica los duplicados heredados) -- la clave es el `Perfil` de ESE
   usuario. Es persistente, sobrevive
   a un cambio de IP del atacante y coincide con la semantica del bloqueo de
   cuenta que ya expone la API (`fecha_desbloqueo`).
2. Si el correo no existe no hay cuenta que bloquear, asi que la clave es el
   `correo normalizado` (sin la IP), guardado en cache con la misma ventana de
   bloqueo. Esto da al atacante exactamente la misma secuencia de 401 y 423
   que con un correo real (requisito anti-enumeracion), sin crear cuentas
   fantasma en la base de datos. El correo se guarda hasheado para no dejar
   direcciones en claro en el cache.

   La clave NO incluye la IP a proposito. Incluirla dejaba un oraculo
   residual: el bloqueo de una cuenta real es global, asi que cinco intentos
   repartidos entre cinco IPs distintas devolvian 423 para un correo
   registrado y seguian devolviendo 401 para uno inexistente -- justo la
   distincion que este contador existe para borrar.

Limites de la estrategia 2, que la vista asume:
  - El contador anonimo vive en el cache, no en la base. Con `LocMemCache`
    (por proceso) varios workers de gunicorn llevan cuentas distintas, y si
    el cache no esta disponible no cuenta nada. Por eso NO es la unica
    defensa: `LoginView` declara `throttle_scope = 'auth_login'` y el limite
    por IP de DRF acota el gasto aunque el cache falle.
  - Un fallo de cache nunca puede tumbar el login (la tabla de
    `DatabaseCache` puede no existir todavia), asi que las lecturas y
    escrituras degradan a "sin memoria" en vez de propagar la excepcion.

Ambas estrategias implementan la misma interfaz para que la vista de login no
tenga que ramificar segun exista o no la cuenta (de esa ramificacion salian
las diferencias de cuerpo y de tiempo que permitian enumerar correos).
"""

import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


def maximo_intentos() -> int:
    return getattr(settings, "MAX_INTENTOS_LOGIN", 5)


def minutos_bloqueo() -> int:
    return getattr(settings, "MINUTOS_BLOQUEO", 15)


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
    """Cuenta en cache por correo normalizado cuando el correo no existe.

    Replica la ventana y el maximo del contador de perfil para que la
    respuesta sea indistinguible de la de una cuenta real, incluyendo el caso
    de intentos repartidos entre varias IPs.
    """

    PREFIJO = "login:intentos:"

    def __init__(self, email: str):
        huella = hashlib.sha256(email.strip().lower().encode()).hexdigest()
        self.clave = f"{self.PREFIJO}{huella}"
        self._estado = self._leer()

    # La entrada vive lo suficiente para cubrir la ventana de bloqueo entera.
    def _ttl(self) -> int:
        return minutos_bloqueo() * 60

    def _leer(self) -> dict:
        vacio = {"fallos": 0, "desbloqueo_en": None}
        try:
            return cache.get(self.clave) or vacio
        except Exception:  # noqa: BLE001
            # Cache caido o tabla de DatabaseCache sin crear: el login tiene
            # que seguir funcionando. Se pierde el conteo anonimo, no la
            # disponibilidad; el limite por IP de la vista sigue en pie.
            logger.warning("Cache no disponible para el conteo de intentos",
                           exc_info=True)
            return vacio

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
        self._escribir(lambda: cache.set(self.clave, self._estado, self._ttl()))

    def intentos_restantes(self) -> int:
        return max(0, maximo_intentos() - self._estado.get("fallos", 0))

    def reiniciar(self) -> None:
        self._escribir(lambda: cache.delete(self.clave))

    @staticmethod
    def _escribir(operacion) -> None:
        try:
            operacion()
        except Exception:  # noqa: BLE001
            logger.warning("No se pudo guardar el conteo de intentos",
                           exc_info=True)


def contador_para(usuario, email: str):
    """Devuelve el contador que corresponde a este intento de login.

    `usuario` es el resultado de resolver el correo contra `auth_user`; si es
    None (o no tiene perfil) se cae al contador anonimo por correo.
    """
    perfil = getattr(usuario, "perfil", None) if usuario is not None else None
    if perfil is not None:
        return ContadorPerfil(perfil)
    return ContadorAnonimo(email)
