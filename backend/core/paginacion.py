"""Paginacion compartida de los listados del panel.

De donde sale
-------------
El catalogo publico (`/api/tienda/catalogo/`) ya paginaba bien: contaba el
total real del filtro, aceptaba `pagina` y calculaba `total_paginas`. El resto
de los listados del panel solo cortaban con `[:limite]` y devolvian
`total = len(datos)`, es decir el tamano de la pagina y no los registros que
cumplian el filtro. Con 1.024 productos eso hacia imposible pasar del 50: no
habia forma de saber que habia mas, ni de pedir la pagina siguiente.

Este modulo extrae ese patron para reusarlo. El catalogo publico tambien lo
usa, pero sigue armando su propia respuesta: sus claves son parte de un
contrato ya publicado y no se tocan.

Orden estable
-------------
`paginar()` exige un queryset ordenado y por un criterio que no empate. Con un
orden ambiguo (solo por `nombre`, con nombres repetidos) MySQL puede devolver
la misma fila en dos paginas distintas y omitir otra: el clasico registro que
"desaparece" al pasar de pagina. Por eso los listados ordenan por
`(nombre, id)`.
"""

from dataclasses import dataclass

# Techo de filas por peticion. Vale para `limite` y para `por_pagina`: ningun
# cliente puede pedir la tabla entera en una sola respuesta.
MAXIMO_POR_PAGINA = 200
POR_PAGINA_POR_DEFECTO = 50


def limite_paginacion(valor, por_defecto: int = POR_PAGINA_POR_DEFECTO,
                      maximo: int = MAXIMO_POR_PAGINA) -> int:
    """Filas por pagina, acotadas a [1, maximo].

    Un valor no numerico o ausente cae en `por_defecto`; `limite=100000` se
    recorta a `maximo` en vez de traer la tabla completa.
    """
    try:
        return max(1, min(int(valor), maximo))
    except (TypeError, ValueError):
        return por_defecto


def numero_de_pagina(valor) -> int:
    """Numero de pagina, siempre >= 1. Un valor invalido cae en la primera."""
    try:
        return max(int(valor), 1)
    except (TypeError, ValueError):
        return 1


@dataclass(frozen=True)
class Pagina:
    """Una pagina de resultados y los contadores para pintar el paginador."""

    objetos: list
    total: int          # registros que cumplen el filtro, NO los de esta pagina
    pagina: int
    por_pagina: int
    total_paginas: int
    desde: int          # 1-based, 0 si la pagina esta vacia
    hasta: int          # 1-based inclusivo, 0 si la pagina esta vacia

    def como_respuesta(self, datos) -> dict:
        """Cuerpo estandar de los listados del panel.

        `datos` son los objetos ya serializados. `total` es el conteo real, lo
        que permite al frontend pintar "Mostrando desde-hasta de total".
        """
        return {
            "resultados": datos,
            "total": self.total,
            "pagina": self.pagina,
            "por_pagina": self.por_pagina,
            "total_paginas": self.total_paginas,
            "desde": self.desde,
            "hasta": self.hasta,
        }


def paginar(queryset, params, por_pagina_por_defecto: int = POR_PAGINA_POR_DEFECTO,
            clave_limite: str = "limite") -> Pagina:
    """Recorta `queryset` a una pagina y calcula los contadores.

    `params` son los `request.query_params`: se leen `pagina` y `limite`.
    El `COUNT(*)` se hace sobre el queryset ya filtrado y antes de recortar,
    para que `total` sea el numero de registros reales.
    """
    por_pagina = limite_paginacion(params.get(clave_limite),
                                   por_defecto=por_pagina_por_defecto)
    pagina = numero_de_pagina(params.get("pagina", 1))

    total = queryset.count()
    total_paginas = max((total + por_pagina - 1) // por_pagina, 1)
    inicio = (pagina - 1) * por_pagina
    objetos = list(queryset[inicio:inicio + por_pagina])

    return Pagina(
        objetos=objetos,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        desde=inicio + 1 if objetos else 0,
        hasta=inicio + len(objetos) if objetos else 0,
    )
