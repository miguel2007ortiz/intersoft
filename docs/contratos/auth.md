# Contrato de `/api/auth/`

Referencia del contrato entre el backend Django y la SPA Angular para
autenticación y sesión. Si cambias una respuesta de `cuentas/views.py`,
actualiza este documento y `frontend/src/app/core/models/auth.model.ts` en el
mismo commit.

Todas las rutas cuelgan de `/api/auth/` (ver `cuentas/urls.py`).

---

## Identificadores: `id` es el del usuario, no el del perfil

Cada cuenta son dos filas: un `auth_user` (la identidad que firma el JWT) y un
`Perfil` (empresa, rol, datos laborales). Son entidades distintas con claves
distintas: `auth_user.id` es un entero autoincremental y `perfil.id` es un
UUID.

| Campo | Qué es | Para qué sirve |
|---|---|---|
| `usuario.id` | `auth_user.id`, el sujeto del token | Identificar a quién pertenece la sesión |
| `usuario.perfil_id` | `perfil.id` (UUID) | Rutas de `/api/seguridad/usuarios/<perfil_id>/` |

Hasta la Fase 2 el login devolvía el id del **perfil** bajo la clave `id`, así
que el frontend creía tener el id del usuario y no tenía forma de obtener el
del perfil. Ambos viajan ahora por separado, y `/auth/me/` usa exactamente las
mismas claves que el login.

> Los ids son cadenas en el JSON (`"1"`, no `1`), porque uno es entero y el
> otro UUID y el frontend los trata igual.

---

## `POST /login/`

Cuerpo: `{ "email": "...", "password": "..." }`. El correo se normaliza a
minúsculas sin espacios antes de resolver la identidad.

### 200 — sesión abierta

```json
{
  "access": "<JWT>",
  "refresh": "<JWT>",
  "usuario": {
    "id": "1",
    "perfil_id": "9f1c...",
    "email": "ana@elprogreso.co",
    "nombre": "Ana Ruiz",
    "rol": "ADMINISTRADOR",
    "empresa": "3a7e...",
    "empresa_nombre": "Tienda El Progreso",
    "debe_cambiar_password": false
  }
}
```

`empresa` y `empresa_nombre` son `null` para los compradores del marketplace,
que no pertenecen a ninguna empresa vendedora.

### Errores

| Código HTTP | `codigo` | Cuándo | Cuerpo |
|---|---|---|---|
| 400 | `DATOS_INVALIDOS` | El correo no es un correo, falta la contraseña | `detalle`, `errores` |
| 401 | `CREDENCIALES_INVALIDAS` | Contraseña incorrecta, correo inexistente, **o cuenta desactivada** | `detalle`, `aviso` opcional |
| 403 | `USUARIO_INACTIVO` | Contraseña correcta pero el perfil está borrado | `codigo` |
| 403 | `EMPRESA_INACTIVA` | Contraseña correcta pero la empresa está desactivada | `codigo` |
| 423 | `CUENTA_BLOQUEADA` | Se agotaron los intentos | `desbloqueo_en` (ISO-8601) |
| 429 | — | Demasiados intentos desde la misma IP (`THROTTLE_LOGIN`) | contrato de error de DRF |

### Reglas del 401 y del 423 que el frontend no debe romper

El 401 es **idéntico** exista o no el correo: mismo código, mismo `detalle` y
nada que permita distinguir los dos casos. Concretamente:

- **No** se devuelve `intentos_restantes`. Decir cuántos intentos quedan
  confirma que el correo está registrado.
- Una cuenta desactivada devuelve el 401 genérico, **no** `USUARIO_INACTIVO`.
  El 403 llega solo cuando la contraseña ya está probada, es decir, a alguien
  que demostró ser el dueño de la cuenta.
- En el último intento antes del bloqueo el cuerpo trae `aviso`, un texto
  genérico sin cifras. Se manda igual para correos inexistentes.
- El 423 llega también para correos que no existen, con su `desbloqueo_en`, y
  el bloqueo no depende de la IP: repartir los intentos entre varias IPs da la
  misma secuencia de códigos en ambos casos.
- Los dos caminos calculan el hash de la contraseña, así que tampoco se
  distinguen por tiempo de respuesta.

El mensaje que ve la persona sale del frontend
(`login.component.html`): el backend solo manda el código y, cuando toca, el
`aviso`.

---

## `GET /me/`

Requiere `Authorization: Bearer <access>`. **Fuente única de la sesión**: el
menú y los guards se arman con `permisos`, nunca deduciendo permisos del
nombre del rol.

```json
{
  "id": "1",
  "perfil_id": "9f1c...",
  "email": "ana@elprogreso.co",
  "nombre": "Ana Ruiz",
  "rol": "ADMINISTRADOR",
  "empresa": "3a7e...",
  "empresa_nombre": "Tienda El Progreso",
  "permisos": ["usuarios.gestionar", "ventas.gestionar"],
  "debe_cambiar_password": false
}
```

403 `SIN_PERFIL` si el usuario autenticado no tiene `Perfil`.

### Consistencia con lo que guarda el navegador

`AuthService` guarda en `localStorage` las claves `intersoft.token`,
`intersoft.refresh`, `intersoft.usuario` e `intersoft.permisos`.

`intersoft.usuario` se escribe en el login **y en cada `cargarMe()`**, que es
lo que corre al arrancar la app tras un F5. Antes solo se escribía en el
login, así que si un administrador cambiaba tu rol o tu empresa seguías con el
menú y los guards del rol viejo hasta cerrar sesión. Como `/auth/me/` devuelve
las mismas claves que el login, su respuesta es la versión de más confianza y
sobrescribe la guardada.

El único punto que escribe esa clave es `guardarUsuario()`, para que el signal
y el `localStorage` no puedan quedar describiendo usuarios distintos.

---

## Resto de rutas

| Ruta | Método | Respuesta | Notas |
|---|---|---|---|
| `/refresh/` | POST | `{ "access": "<JWT>" }` | Limitado por IP (`auth_refresh`) |
| `/cambiar-password/` | POST | 200 sin cuerpo | 400 `PASSWORD_ACTUAL_INCORRECTA` si la actual no coincide |
| `/registro/` | POST | 201 sin cuerpo | Crea empresa + administrador |
| `/registro/comprador/` | POST | 201 sin cuerpo | Comprador del marketplace, sin empresa |
| `/email-disponible/` | GET | `{ "disponible": bool }` | Ignora mayúsculas |
| `/password-reset/` | POST | **siempre** 200 sin cuerpo | Responde igual exista o no el correo (anti-enumeración) |
| `/password-reset/confirmar/` | POST | 200 sin cuerpo | 400 `TOKEN_INVALIDO` si venció o ya se usó |

## Formato de error

Los errores de validación siguen el contrato común de la API
(`core/exceptions.py`):

```json
{ "codigo": "DATOS_INVALIDOS", "detalle": "Texto para la persona.", "errores": { "email": ["..."] } }
```

`errores` solo aparece cuando hay errores por campo.
