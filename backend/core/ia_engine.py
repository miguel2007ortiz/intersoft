"""Motor del asistente IA (fase 8).

Separa la construccion del "contexto de negocio" (datos agregados de la
empresa que se pasan al modelo) de la llamada al proveedor, que es
configurable por variables de entorno:

    IA_PROVIDER  -> 'mock' (por defecto) o 'openai' (API compatible)
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

import json
import logging
import urllib.request

from django.conf import settings

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
    """
    # Import perezoso para evitar dependencias circulares.
    from . import analytics  # noqa: F401  (se usa para las vistas)

    # El resumen usa los filtros del request (rango de fechas/categoria).
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
    return ContextoEmpresa(empresa=empresa, resumen=resumen,
                           top_productos=top, clientes_frecuentes=clientes,
                           bajo_minimo=bajo)


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


def _mensajes(historial, pregunta):
    """Construye la lista de mensajes para el proveedor.

    `historial` son tuplas (rol, contenido) de la conversacion; se recorta
    a los ultimos `IA_MAX_HISTORIAL` turnos para acotar el payload.
    """
    max_turnos = getattr(settings, 'IA_MAX_HISTORIAL', 10)
    mensajes = [{"role": "system",
                 "content": "Asistente de gestion empresarial InterSoft. "
                            "Responde en espanol, conciso y basandote solo en "
                            "el contexto de negocio proporcionado. No inventes "
                            "datos que no esten en el contexto."}]
    for rol, contenido in historial[-max_turnos:]:
        # El rol almacenado ('usuario'|'asistente') coincide con el payload.
        mensajes.append({"role": rol, "content": contenido})
    mensajes.append({"role": "usuario", "content": pregunta})
    return mensajes


def llamar_proveedor(contexto, historial, pregunta) -> str:
    """Invoca al proveedor configurado y devuelve la respuesta de texto.

    Levanta `IATimeoutError`/`IAError` si el proveedor falla o no hay clave.
    """
    if getattr(settings, 'IA_PROVIDER', 'mock') == 'openai':
        return _llamar_openai(contexto, historial, pregunta)
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
        "Para respuestas inteligentes reales, define IA_PROVIDER=openai e "
        "IA_API_KEY. Tu pregunta fue: " + pregunta
    )


# ---------------------------- Proveedor OpenAI ------------------------------

def _llamar_openai(contexto, historial, pregunta) -> str:
    api_key = getattr(settings, 'IA_API_KEY', '')
    if not api_key:
        raise IATimeoutError(
            "El proveedor openai esta activo pero falta IA_API_KEY.")
    url = getattr(settings, 'IA_API_URL', '') or \
        'https://api.openai.com/v1/chat/completions'
    payload = {
        "model": getattr(settings, 'IA_MODEL', 'gpt-3.5-turbo'),
        "messages": _mensajes(historial, pregunta),
        "temperature": 0.4,
    }
    cuerpo = json.dumps(payload).encode('utf-8')
    peticion = urllib.request.Request(
        url, data=cuerpo, method='POST',
        headers={
            "Content-Type": "application/json",
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
    except (KeyError, IndexError, TypeError) as exc:
        raise IAError("El proveedor devolvio una respuesta inesperada.")
