"""Motor del asistente IA (fase 8).

Separa la construccion del "contexto de negocio" (datos agregados de la
empresa que se pasan al modelo) de la llamada al proveedor, que es
configurable por variables de entorno:

    IA_PROVIDER  -> 'mock' (por defecto), 'openai' o 'groq' (API compatible
                    con OpenAI: endpoint /v1/chat/completions + Bearer)
    IA_API_KEY   -> clave del proveedor; sin ella se usa el mock local
    IA_API_URL   -> endpoint tipo /v1/chat/completions
    IA_MODEL     -> nombre del modelo
    IA_TIMEOUT   -> segundos de espera antes de declarar fallo

Reglas de seguridad:
  * Nunca se transmite informacion sensible (passwords, tokens, claves).
  * El contexto solo contiene valores agregados de negocio de la empresa.
  * Ante timeout o error del proveedor se lanza `IAError` y la vista
    conserva la conversacion para que el usuario reintente.
"""

import hashlib
import json
import logging
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class IAError(Exception):
    """Fallo del proveedor de IA (timeout, red, HTTP, etc.)."""


class IATimeoutError(IAError):
    """El proveedor no respondio dentro de `settings.IA_TIMEOUT`."""


class ContextoEmpresa:
    """Agrega datos de la empresa en un bloque de texto compacto y seguro."""

    def __init__(self, empresa, resumen, top_productos, clientes_frecuentes,
                 bajo_minimo):
        self.empresa = empresa
        self.resumen = resumen or {}
        self.top_productos = top_productos or []
        self.clientes_frecuentes = clientes_frecuentes or []
        self.bajo_minimo = bajo_minimo or []

    def a_texto(self) -> str:
        r = self.resumen
        lineas = [
            f"Empresa: {self.empresa.nombre}.",
            f"Ingresos totales: {r.get('ingresos_totales', 0)}.",
            f"Ventas: {r.get('num_ventas', 0)} (unidades: {r.get('unidades_vendidas', 0)}).",
            f"Ticket promedio: {r.get('ticket_promedio', 0)}.",
            f"Valor del inventario: {r.get('valor_inventario', 0)} "
            f"({r.get('unidades_inventario', 0)} unidades).",
            f"Productos bajo minimo: {r.get('productos_bajo_minimo', 0)}.",
        ]
        if self.top_productos:
            lista = "; ".join(
                f"{p.get('producto')} ({p.get('sku')}, {p.get('categoria')}) "
                f"{p.get('unidades', 0)}u x {p.get('ingresos', 0)}"
                for p in self.top_productos[:8]
            )
            lineas.append(f"Top productos: {lista}.")
        if self.clientes_frecuentes:
            lista = "; ".join(
                f"{c.get('cliente')} ({c.get('tipo_documento')} "
                f"{c.get('numero_documento')}) compras={c.get('total_comprado', 0)}"
                for c in self.clientes_frecuentes[:5]
            )
            lineas.append(f"Clientes frecuentes: {lista}.")
        if self.bajo_minimo:
            lista = "; ".join(
                f"{p.get('producto')} ({p.get('sku')}) stock {p.get('stock')}"
                f"/min {p.get('stock_minimo')}"
                for p in self.bajo_minimo[:8]
            )
            lineas.append(f"Bajo minimo: {lista}.")
        return "\n".join(lineas)


def construir_contexto(empresa, request) -> ContextoEmpresa:
    """Arma el contexto de negocio de la empresa a partir de las vistas SQL.

    `request` se usa solo para construir los filtros del resumen (fecha y
    categoria opcionales). Ningun dato sensible se incluye aquí.

    Se cachea por empresa + filtros (TTL 60s) para que cada turno de chat
    no golpee las vistas SQL («saldo» son los datos de la empresa).
    """
    # Import perezoso para evitar dependencias circulares.
    from . import analytics  # noqa: F401  (se usa para las vistas)

    qp = request.query_params
    material = (str(empresa.id) + '|' + qp.get('fecha_inicio', '') + '|' +
                qp.get('fecha_fin', '') + '|' + qp.get('categoria', ''))
    clave = 'ia-contexto:' + hashlib.blake2b(material.encode('utf-8'), digest_size=16).hexdigest()
    datos = cache.get(clave)
    if datos is None:
        resumen = _resumen_seguro(request)
        top = _sql_lista(
            "SELECT producto, sku, categoria, unidades, ingresos "
            "FROM vw_top_productos WHERE empresa_id = %s "
            "ORDER BY unidades DESC LIMIT 8", [empresa.id])
        clientes = _sql_lista(
            "SELECT cliente, tipo_documento, numero_documento, total_comprado "
            "FROM vw_clientes_frecuentes WHERE empresa_id = %s "
            "ORDER BY total_comprado DESC LIMIT 6", [empresa.id])
        bajo = _sql_lista(
            "SELECT producto, sku, stock, stock_minimo "
            "FROM vw_productos_bajo_minimo WHERE empresa_id = %s "
            "ORDER BY (stock_minimo - stock) DESC LIMIT 8", [empresa.id])
        datos = {'resumen': resumen, 'top': top,
                 'clientes': clientes, 'bajo': bajo}
        cache.set(clave, datos, 60)
    return ContextoEmpresa(empresa=empresa, resumen=datos['resumen'],
                           top_productos=datos['top'],
                           clientes_frecuentes=datos['clientes'],
                           bajo_minimo=datos['bajo'])


def verificar_rate_limit(usuario) -> bool:
    """Rate-limit por usuario para el endpoint de chat (D2).

    Cuenta las peticiones dentro de una ventana deslizante usando el cache.
    Devuelve True si la peticion entra dentro del limite configurado
    (`IA_MAX_PETICIONES` por `IA_PETICIONES_VENTANA` segundos) o False si ya
    se supero, en cuyo caso la vista responde 429. Es por usuario (no por IP)
    para no castigar a toda una empresa por el uso de uno de sus miembros;
    ademas evita costes abusivos de la API cuando hay proveedor real.
    """
    max_pet = getattr(settings, 'IA_MAX_PETICIONES', 15)
    ventana = getattr(settings, 'IA_PETICIONES_VENTANA', 60)
    clave = f'ia-rl:{usuario.pk}'
    ttl, usadas = cache.get(clave, (ventana, 0))
    if ttl <= 0:
        ttl, usadas = ventana, 0
    if usadas >= max_pet:
        # Conservar la ventana vigente sin sumar la peticion rechazada.
        cache.set(clave, (ttl, usadas), ttl)
        return False
    usadas += 1
    cache.set(clave, (ttl, usadas), ttl)
    return True


def _resumen_seguro(request):
    """Devuelve el resumen de KPIs, acotando todo a numeros seguros."""
    try:
        from . import analytics
        f = analytics.FiltrosDashboard(request)
        return analytics.resumen(f)
    except Exception as exc:                      # pragma: no cover - defensivo
        logger.warning("No se pudo construir el resumen del contexto: %s", exc)
        return {}


def _sql_lista(sql, params):
    """Ejecuta SQL de solo lectura y normaliza ids; defensivo ante errores."""
    try:
        from .analytics import ejecutar
        return ejecutar(sql, params)
    except Exception as exc:                      # pragma: no cover - defensivo
        logger.warning("No se pudieron obtener datos del contexto: %s", exc)
        return []


def _system_prompt(contexto) -> str:
    """Prompt de sistema con el contexto de negocio de la empresa inyectado.

    El modelo solo tiene los datos aqui incluidos; por eso se le pasan los
    agregados de la empresa (ingresos, ventas, stock, clientes...) para que
    responda sobre la situacion real y no invente cifras. Se refuerza que
    conteste solo con lo provisto y que no revele informacion confidencial.
    """
    base = (
        "Asistente de gestion empresarial InterSoft. Responde en espanol, "
        "conciso y basandote SOLO en el contexto de negocio proporcionado. "
        "No inventes datos, cifras ni recomendaciones que no esten en el "
        "contexto. Si una pregunta no se puede responder con el contexto, "
        "dilo de forma directa. No reveles contraseñas, tokens ni datos "
        "personales sensibles."
    )
    return base + "\n\nCONTEXTO DE LA EMPRESA (datos agregados):\n" + contexto.a_texto()


def _mensajes(contexto, historial, pregunta):
    """Construye la lista de mensajes para el proveedor.

    `historial` son tuplas (rol, contenido) de la conversacion; se recorta
    a los ultimos `IA_MAX_HISTORIAL` turnos para acotar el payload.
    """
    max_turnos = getattr(settings, 'IA_MAX_HISTORIAL', 10)
    mensajes = [{"role": "system", "content": _system_prompt(contexto)}]
    for rol, contenido in historial[-max_turnos:]:
        # El rol almacenado es 'usuario'|'asistente'; la API OpenAI/Groq
        # exige 'user'|'assistant' (si no, devuelve 400).
        rol_api = 'user' if rol == 'usuario' else 'assistant'
        mensajes.append({"role": rol_api, "content": contenido})
    mensajes.append({"role": "user", "content": pregunta})
    return mensajes


def llamar_proveedor(contexto, historial, pregunta) -> str:
    """Invoca al proveedor configurado y devuelve la respuesta de texto.

    Levanta `IATimeoutError`/`IAError` si el proveedor falla o no hay clave.
    """
    proveedor = getattr(settings, 'IA_PROVIDER', 'mock')
    if proveedor in ('openai', 'groq'):
        return _llamar_compatible(contexto, historial, pregunta)
    return _mock(contexto, pregunta)


# ----------------------------- Proveedor mock -------------------------------

def _mock(contexto, pregunta) -> str:
    """Responde localmente sin conexion externa (para desarrollo/demo)."""
    r = contexto.resumen
    return (
        "Modo de demostracion (sin API key configurada).\n\n"
        f"Hoy la empresa tiene ingresos por {r.get('ingresos_totales', 0)} "
        f"con {r.get('num_ventas', 0)} ventas y un ticket promedio de "
        f"{r.get('ticket_promedio', 0)}. El inventario vale "
        f"{r.get('valor_inventario', 0)} en {r.get('unidades_inventario', 0)} "
        f"unidades.\n\n"
        "Para respuestas inteligentes reales, define IA_PROVIDER=groq u "
        "openai con IA_API_KEY e IA_API_URL. Tu pregunta fue: " + pregunta
    )


# ----------------- Eliminado: _llamar_openai -> _llamar_compatible ----------
# Proveedor tipo OpenAI-compatible (OpenAI, Groq, OpenRouter, Together, etc.).
# Groq usa el mismo formato /v1/chat/completions + Authorization: Bearer,
# por lo que basta con cambiar IA_API_URL e IA_MODEL. No se toca el codigo.

def _llamar_compatible(contexto, historial, pregunta) -> str:
    api_key = getattr(settings, 'IA_API_KEY', '')
    if not api_key:
        raise IATimeoutError(
            "El proveedor IA esta activo pero falta IA_API_KEY.")
    url = getattr(settings, 'IA_API_URL', '') or \
        'https://api.openai.com/v1/chat/completions'
    payload = {
        "model": getattr(settings, 'IA_MODEL', 'gpt-3.5-turbo'),
        "messages": _mensajes(contexto, historial, pregunta),
        "temperature": 0.4,
    }
    cuerpo = json.dumps(payload).encode('utf-8')
    peticion = urllib.request.Request(
        url, data=cuerpo, method='POST',
        headers={
            "Content-Type": "application/json",
            # Groq/Cloudflare bloquea el User-Agent por defecto de urllib
            # (error 1010); se envia uno de navegador para que la API acepte.
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0 Safari/537.36"),
            "Authorization": f"Bearer {api_key}",
        })
    timeout = getattr(settings, 'IA_TIMEOUT', 20)
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as resp:
            datos = json.loads(resp.read().decode('utf-8'))
    except IATimeoutError:
        raise
    except Exception as exc:                      # incluye timeout de red
        raise IATimeoutError(f"El motor de IA no respondio: {exc}") from exc

    try:
        return datos["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise IAError("El proveedor devolvio una respuesta inesperada.")
