# Cuentas

Autenticacion y control de acceso de InterSoft. API expuesta bajo `/api/auth/`
y consumida por el frontend Angular.

## Modelos
- `Perfil`: vincula la cuenta (tabla `auth_user` de Django) con su empresa y rol.
  Guarda tambien el estado de bloqueo por intentos fallidos de login.
- `Rol`: roles base de la plataforma: ADMINISTRADOR, EMPLEADO y CLIENTE.
- `Permiso` / `RolPermiso`: catalogo de permisos (`ventas.gestionar`, ...) y su
  asignacion a cada rol.
- `ActividadUsuario`: auditoria automatica. Toda escritura autenticada queda
  registrada aqui (middleware `cuentas.middleware.AuditoriaMiddleware`) junto
  con los eventos de login y recuperacion que emiten las vistas.
- `TokenRecuperacion`: token hasheado (SHA-256) para restablecer contrasena,
  vence en 30 minutos y de un solo uso.

## Autenticacion (JWT - SimpleJWT)
- `POST /api/auth/login/` -> access + refresh + datos del usuario.
  Bloquea la cuenta 15 minutos tras 5 intentos fallidos (ver
  `MAX_INTENTOS_LOGIN` y `MINUTOS_BLOQUEO` en settings).
- `GET /api/auth/email-disponible/?email=` -> disponibilidad de correo.
- `POST /api/auth/password-reset/` -> envia enlace de recuperacion al correo.
- `POST /api/auth/password-reset/confirmar/` -> cambia la contrasena con el token.

## Comandos
- `python manage.py seed_roles`: crea los 3 roles y sus permisos (idempotente).
