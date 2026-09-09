"""Cache de negocio por version por empresa (Fase B1).

Reemplaza la invalidacion global (``cache.clear()``) por un contador de
generacion por namespace y alcance: las claves se prefijan con la generacion
vigente y "invalidar" solo incrementa el contador. Asi la invalidacion es
O(1), NO borra datos de otros tenants, ni el contexto IA, ni los contadores
de rate-limit del chat (que viven como claves sueltas), y funciona igual con
LocMemCache (tests), cache por BD MySQL o Redis.

- Namespace: que se guarda ('analitica', 'ia', 'cat').
- Alcance: a que pertenecen las claves ('<empresa_id>' o 'global').

Las claves viejas quedan huerfanas y expiran solas por su TTL (<= 60s hoy),
asi que un salto de generacion actua como invalidacion inmediata sin borrar
nada de otros buckets.
"""

from django.core.cache import cache

# Los contadores de generacion duran una semana (refresco perezoso); la
# invalidacion nunca depende de su expiracion sino de su incremento.
GEN_TTL = 7 * 24 * 3600


def generacion(namespace: str, alcance: str) -> str:
    """Generacion vigente para un namespace+alcance (arranca en 1)."""
    return str(cache.get_or_set(f'gen:{namespace}:{alcance}', 1, GEN_TTL))


def invalidar(namespace: str, alcance: str) -> None:
    """Incrementa la generacion: las claves prefijadas quedan obsoletas."""
    cache.set(f'gen:{namespace}:{alcance}',
              int(generacion(namespace, alcance)) + 1, GEN_TTL)


def invalidar_empresa(empresa_id) -> None:
    """Invalida analitica e IA-contexto de una empresa (al crear/modificar
    ventas, lineas, movimientos de inventario o productos)."""
    invalidar('analitica', str(empresa_id))
    invalidar('ia', str(empresa_id))


def invalidar_catalogo() -> None:
    """Invalida el catalogo publico (namespace 'cat', alcance 'global')."""
    invalidar('cat', 'global')