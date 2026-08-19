"""
Fallback de base de datos para Windows.

mysqlclient no siempre compila en Windows. Si no esta instalado y PyMySQL
si, instalamos PyMySQL como conector compatible con MySQLdb. Asi el mismo
codigo funciona con cualquiera de los dos.
"""
try:
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql  # noqa: F401
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
