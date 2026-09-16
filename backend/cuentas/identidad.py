"""Resolucion de identidad por correo, y deteccion de identidades ambiguas.

El login resuelve la identidad por correo y `authenticate()` la resuelve por
`username` (el USERNAME_FIELD de Django). Si dos filas coinciden en cualquiera
de las dos columnas ignorando mayusculas, el contexto (empresa, rol, permisos)
y el conteo de intentos fallidos pueden acabar en una cuenta distinta de la
que se esta abriendo: es el BUG-09.

La comparacion se hace con LOWER() a proposito y no se delega en la collation
de la base. En MySQL la collation por defecto (`utf8mb4_0900_ai_ci`) ya ignora
mayusculas, pero eso es una propiedad del despliegue, no del esquema: una base
creada con `utf8mb4_bin` -- o un cambio de motor -- reabriria el agujero sin
que ninguna migracion lo notara.
"""

# Columnas por las que se puede resolver una identidad al iniciar sesion.
# `email` ignora las vacias: Django permite `email=''` y esas filas no
# identifican a nadie (ver el NULLIF del indice funcional en la migracion).
CONSULTAS = {
    "email": (
        "SELECT LOWER(email) AS valor, COUNT(*) AS cuantos, "
        "       GROUP_CONCAT(id ORDER BY id) AS ids "
        "FROM auth_user WHERE email <> '' "
        "GROUP BY LOWER(email) HAVING COUNT(*) > 1 ORDER BY cuantos DESC"
    ),
    "username": (
        "SELECT LOWER(username) AS valor, COUNT(*) AS cuantos, "
        "       GROUP_CONCAT(id ORDER BY id) AS ids "
        "FROM auth_user "
        "GROUP BY LOWER(username) HAVING COUNT(*) > 1 ORDER BY cuantos DESC"
    ),
}


def buscar(cursor) -> dict:
    """Devuelve {columna: [(valor, cuantos, ids), ...]} solo con lo repetido."""
    hallazgos = {}
    for columna, sql in CONSULTAS.items():
        cursor.execute(sql)
        filas = cursor.fetchall()
        if filas:
            hallazgos[columna] = filas
    return hallazgos


def describir(hallazgos: dict) -> str:
    """Texto accionable: que columna, que valor y que ids hay que arreglar."""
    lineas = []
    for columna, filas in hallazgos.items():
        lineas.append(f"Columna `{columna}` (ignorando mayusculas):")
        lineas.extend(
            f"  - {valor}: {cuantos} cuentas (auth_user.id = {ids})"
            for valor, cuantos, ids in filas
        )
    return "\n".join(lineas)


def normalizar_correo(valor: str) -> str:
    """Forma canonica de un correo: sin espacios y en minusculas."""
    return (valor or "").strip().lower()


def por_correo(modelo_o_queryset, email: str):
    """Filtra usuarios por correo ignorando mayusculas, sin depender de la
    collation.

    `iexact` se traduce en MySQL a un LIKE cuya sensibilidad la decide la
    collation del despliegue; `LOWER()` se comporta igual en cualquiera y es
    la expresion que indexa `0012_email_unico_sin_mayusculas`, asi que la
    busqueda sigue usando indice en vez de recorrer la tabla.
    """
    from django.db.models.functions import Lower

    queryset = getattr(modelo_o_queryset, "objects", modelo_o_queryset)
    return (queryset.alias(_correo=Lower("email"))
            .filter(_correo=normalizar_correo(email)))
