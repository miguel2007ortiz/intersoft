# 🏪 InterSoft — Backend Django

Plataforma SaaS de gestión empresarial multi-tenant para pequeños negocios de Colombia.
Proyecto **SENA ADSO 2026**.

> Fase 1 (MVP): 5 modelos núcleo — Empresa, Usuario, Producto, Cliente, Venta.

---

## 📋 Requisitos previos

- **Python 3.14.6** (versión objetivo del proyecto)
- **MySQL 8** (servidor corriendo)
- **pip** y **venv**

### ⚠️ Compatibilidad Python ↔ Django (leer antes de instalar)

Esto es lo que más rompe proyectos al usar una versión nueva de Python:
**no todas las versiones de Django soportan Python 3.14.**

| Django | Soporta Python 3.14 | Soporte hasta |
|--------|:---:|---|
| 4.2 LTS | ❌ **No** | abril 2026 |
| 5.1 | ❌ No | diciembre 2025 |
| **5.2 LTS** | ✅ **Sí** (primera versión compatible) | **abril 2028** ← usamos esta |
| 6.0 | ✅ Sí (requiere 3.12+) | ~abril 2027 |

**Este proyecto usa Django 5.2 LTS.** El `requirements.txt` ya lo fija así.
Elegimos LTS porque tiene soporte de seguridad hasta 2028 y mayor
compatibilidad con librerías de terceros.

> `manage.py` verifica tu versión de Python al arrancar y avisa si no coincide.

---

## 🚀 Instalación paso a paso

### 1. Descomprime el proyecto y entra a la carpeta

```bash
cd intersoft-backend
```

### 2. Crea y activa el entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

> **¿Falla `mysqlclient` en Windows?**
> Necesitas `mysqlclient` 2.3.0 o superior (las anteriores no compilan en
> Python 3.14). Instala primero las *build tools* de Visual C++, o usa la
> alternativa pura en Python:
> `pip install PyMySQL` y añade al inicio de `intersoft/__init__.py`:
> ```python
> import pymysql
> pymysql.install_as_MySQLdb()
> ```

### 4. Crea la base de datos en MySQL

```bash
mysql -u root -p
```

```sql
CREATE DATABASE intersoft_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 5. Configura las variables de entorno

```bash
# Copia la plantilla
cp .env.example .env     # (Windows: copy .env.example .env)
```

Abre `.env` y pon tu contraseña de MySQL en `DB_PASSWORD`.

### 6. Aplica las migraciones (crea las tablas)

```bash
python manage.py makemigrations core
python manage.py migrate
```

### 7. Carga datos de demostración

```bash
python manage.py seed_demo
```

### 8. Crea un superusuario (para el admin)

```bash
python manage.py createsuperuser
```

### 9. Arranca el servidor

```bash
python manage.py runserver
```

Abre en tu navegador:

| URL | Qué verás |
|-----|-----------|
| http://localhost:8000/registro/ | **Registrar tu negocio** (crea empresa + cuenta) |
| http://localhost:8000/login/ | **Iniciar sesión** |
| http://localhost:8000/ | Dashboard con KPIs (requiere login) |
| http://localhost:8000/productos/ | Inventario |
| http://localhost:8000/ventas/ | Ventas |
| http://localhost:8000/clientes/ | Clientes |
| http://localhost:8000/admin/ | Panel de administración de Django |

> **Cuenta de prueba** (si corriste `seed_demo`):
> Usuario: `demo` · Contraseña: `demo12345`

---

## 🧱 Estructura del proyecto

```
intersoft-backend/
├── intersoft/              # Configuración del proyecto
│   ├── settings.py         # MySQL + variables de entorno
│   ├── urls.py             # Rutas principales
│   ├── wsgi.py / asgi.py   # Servidores
├── core/                   # App de negocio
│   ├── models.py           # ⭐ Los 5 modelos + Perfil (login)
│   ├── views.py            # Lógica de páginas + registro/login/logout
│   ├── urls.py             # Rutas de la app
│   ├── forms.py            # Formularios (incluye registro de empresario)
│   ├── admin.py            # Configuración del admin
│   ├── signals.py          # Alerta de stock bajo
│   ├── tests.py            # Pruebas automáticas
│   ├── management/commands/
│   │   └── seed_demo.py    # Comando de datos demo
│   ├── static/core/css/
│   │   └── styles.css      # ⭐ CSS separado del HTML
│   └── templates/core/     # Plantillas HTML (Bootstrap 5)
│       ├── base.html       # Layout con sidebar
│       ├── login.html      # Inicio de sesión
│       ├── registro.html   # Registro de empresario
│       └── ...
├── media/                  # Imágenes subidas
├── requirements.txt        # Dependencias
├── .env.example            # Plantilla de variables
└── .gitignore
```

---

## 🧪 Ejecutar las pruebas

```bash
python manage.py test core
```

---

## 🗺️ Decisiones de arquitectura

| Decisión | Por qué |
|----------|---------|
| **UUID como PK** | Oculta el tamaño del negocio, evita enumeración de registros. |
| **Soft delete** (`deleted_at`) | Nunca se pierde trazabilidad ni historial. |
| **`fk_empresa` en todo** | Aislamiento multi-tenant: cada empresa solo ve sus datos. |
| **Clase base `TimeStampedModel`** | Evita repetir `id`, timestamps y borrado lógico. |
| **Variables en `.env`** | Las credenciales nunca quedan en el código. |
| **`signals.py`** | Replica en Python la alerta de stock que en SQL era un trigger. |
| **`Perfil` + User de Django** | El login usa el sistema seguro de Django (hashing, sesiones); `Perfil` conecta cada usuario con su empresa. No se reinventa la seguridad. |
| **Django 5.2 LTS** | Primera versión compatible con Python 3.14 y con soporte hasta 2028. Django 4.2 simplemente no arranca en 3.14. |
| **CSS en archivo estático** | La decoración vive en `static/core/css/styles.css`, separada del HTML. Se carga con `{% static %}`. |

---

## 🔜 Siguientes pasos (Fase 2)

1. **Autenticación real** — login/logout con el `User` de Django.
2. **Modelo `DetalleVenta`** — ítems por venta + descuento de stock atómico.
3. **API REST** — endpoints JSON con Django REST Framework para el frontend React.
4. **Roles y permisos** — RBAC completo (módulo Auth del MER).
5. **Despliegue** — Gunicorn + Nginx en un VPS, o Railway/Render.

---

**Autores:** Daniel Velasco · Miguel Ortiz
**Instructora:** Paola Andrea Gutiérrez Mendieta
**Programa:** ADSO — SENA 2026
