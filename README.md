# InterSoft

Plataforma SaaS de gestion empresarial multi-tenant para MiPymes.
Backend **Django 5.2 + DRF + JWT** sobre **MySQL 8**, frontend **Angular 22** (standalone + signals).

Construido siguiendo la guia `intersoftdaniel.docx`.

---

## 1. Requisitos

| Herramienta | Version minima | Nota |
|---|---|---|
| Python | 3.10+ | marca "Add python.exe to PATH" al instalar |
| Node.js | 22.22.3+ | Angular 22 lo exige; con 22.22.2 el CLI se niega a arrancar |
| Angular CLI | 22 | `npm install -g @angular/cli` |
| Laragon (MySQL 8) | Full | solo se usa el servicio de MySQL |

## 2. Base de datos

Abre Laragon → **Start All**, luego click derecho en el icono → *Database* (HeidiSQL) y ejecuta:

```sql
CREATE DATABASE intersoft_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Credenciales de fabrica de Laragon: `root` / sin contraseña / `127.0.0.1:3306`.

## 3. Backend

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

python manage.py makemigrations core cuentas
python manage.py migrate
python manage.py seed_demo          :: datos de ejemplo (opcional)
python manage.py createsuperuser    :: para entrar a /admin/
python manage.py runserver          :: http://127.0.0.1:8000
```

> Si `pip install mysqlclient` falla en Windows (falta Visual C++ Build Tools),
> no pasa nada: `intersoft/__init__.py` detecta la ausencia y activa **PyMySQL**
> automaticamente como conector compatible.

## 4. Frontend

```bat
cd frontend
npm install
npm start                           :: http://localhost:4200
```

## 5. Flujo para probar

1. Home publico → **Crear cuenta**.
2. Registro (empresa + administrador) → redirige a `/login?registrado=1` con el aviso "Cuenta creada".
3. Login → efecto de bienvenida animado (2.4 s) → `/dashboard`.
4. Dashboard: saludo, datos del usuario en el header, **Cerrar sesion**.
5. `/recuperar` con un correo registrado → el enlace se imprime en la consola de Django
   (no hay SMTP real en desarrollo).

Cuenta de demostracion tras `seed_demo`: **ana@elprogreso.co / demo12345**.

## 6. Contrato de la API

Todo cuelga de `/api/auth/`.

| Metodo | Ruta | Respuestas |
|---|---|---|
| POST | `login/` | 200 `{access, refresh, usuario}` · 401 `CREDENCIALES_INVALIDAS` · 423 `CUENTA_BLOQUEADA` · 403 `USUARIO_INACTIVO` |
| POST | `registro/` | 201 · 400 `DATOS_INVALIDOS` |
| GET | `email-disponible/?email=` | 200 `{disponible}` |
| POST | `password-reset/` | **siempre** 200 |
| POST | `password-reset/confirmar/` | 200 · 400 `TOKEN_INVALIDO` / `DATOS_INVALIDOS` |

Decisiones de seguridad que conviene poder sustentar:

- **Mismo mensaje** para correo inexistente y contraseña errada → no se puede enumerar usuarios.
- La solicitud de recuperacion responde **200 siempre**, exista o no la cuenta.
- El bloqueo se verifica **antes** de comprobar la contraseña (5 intentos → 15 min).
- En la base de datos se guarda solo el **hash SHA-256** del token de recuperacion, nunca el token en claro.
- El guard de Angular es experiencia de usuario, **no** seguridad: la autorizacion la hace Django en cada endpoint.

## 7. Estado del proyecto

**Ya construido**

- Backend: login, registro, recuperacion con bloqueo por intentos fallidos (JWT).
- Frontend: sesion, registro, recuperacion/restablecimiento, dashboard protegido por guard.
- Dominio: Empresa, Usuario, Categoria, Producto, Cliente, Venta (modelos + admin).
- Efecto de bienvenida animado, aviso de cookies, sistema de diseño (verde institucional).

**Pendiente (se honesto si sustentas esto)**

- Endpoints REST del dominio de negocio (productos, clientes, ventas): hoy solo son modelos + admin.
- SMTP real: el correo de recuperacion se imprime en consola.
- Renovacion automatica del access token con el refresh token.
- Throttling por IP en el endpoint de recuperacion.
- Pruebas automatizadas.
- `core.Usuario` quedo como legado del MVP; la autenticacion real usa el `User` de Django via `cuentas.Perfil`.

## 8. Estructura

```
intersoft/
├─ backend/
│  ├─ intersoft/      settings, urls, fallback PyMySQL
│  ├─ core/           dominio de negocio + admin + signals + seed_demo
│  ├─ cuentas/        Perfil, TokenRecuperacion, serializers, 5 vistas
│  ├─ requirements.txt
│  └─ .env.example
└─ frontend/
   └─ src/app/
      ├─ core/        models, services (auth, welcome), guard, interceptor, validators
      ├─ shared/      welcome-overlay, cookie-banner, layout/auth-shell
      └─ features/    home, auth/{login,recuperar,restablecer}, registro, dashboard
```
