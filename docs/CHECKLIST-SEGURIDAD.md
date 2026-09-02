# Checklist de seguridad y despliegue — InterSoft

Lista de verificación pre-despliegue y operativa. Marca cada ítem antes de
publicar. Refleja exactamente lo que el proyecto ya implementa (verificado en
`settings.py`, guards del frontend y la suite de pruebas).

---

## 1. Antes de desplegar (obligatorio)

- [ ] `DEBUG=False` en el entorno real (la app **falla al arrancar** con el
      placeholder de desarrollo o sin `SECRET_KEY`).
- [ ] `SECRET_KEY` aleatoria generada con
      `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
      y guardada **solo** en el entorno/secrets del servidor (nunca en git).
- [ ] `ALLOWED_HOSTS` lista los dominios públicos reales, separados por coma y
      **sin** `*`.
- [ ] `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` con las URL reales del
      frontend (HTTPS), no `http://localhost:4200`.
- [ ] Con `DEBUG=False` se activan solas (no se deben apagar):
      `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
      `SECURE_HSTS_*` (1 año), `X_FRAME_OPTIONS=DENY`,
      `SECURE_PROXY_SSL_HEADER`.
- [ ] El servidor/buffer termina TLS (proxy inverso) y reenvía
      `X-Forwarded-Proto: https` (requerido por `SECURE_PROXY_SSL_HEADER`).
- [ ] Sin secretos en el repo: `.gitignore` cubre `.env`, `*.pem`, `*.key`,
      `*.p12`, `secrets/`, logs y media. Verificar con:
      `git ls-files | grep -E '\.env$|\.pem$|\.key$'` → **vacío**.
- [ ] Credenciales SMTP/WhatsApp/IA reales **no** versionadas; solo en el
      entorno (`EMAIL_HOST_PASSWORD`, `WA_TOKEN`, `IA_API_KEY`).

## 2. Backend (Django)

- [ ] `python manage.py check` → "System check identified no issues".
- [ ] `python manage.py makemigrations --check --dry-run` → "No changes detected"
      (sin migraciones pendientes).
- [ ] Backup de la base previo a migrar y `python manage.py migrate --plan`
      antes de aplicar (ver `backend/README.md`).
- [ ] `python manage.py test` → suite completa en verde (241 tests).
- [ ] Autenticación: JWT `ACCESS_TOKEN_LIFETIME=30m`, `REFRESH=7d`; bloqueo de
      login tras 5 intentos (`MAX_INTENTOS_LOGIN`) por 15 min
      (`MINUTOS_BLOQUEO`); reset de password expira en 30 min.
- [ ] Maniobras de seguridad HTTP activas con o sin HTTPS: cookies
      `HttpOnly` + `SameSite=Lax`, `X_FRAME_OPTIONS=DENY`, manejador de
      excepciones global sin tracebacks.
- [ ] Aislamiento multi-tenant verificado: cada vista filtra por `empresa_id`;
      roles visibles = globales + propios (`roles_visibles`); hay pruebas de
      regresión de aislamiento entre empresas.
- [ ] Concurrencia controlada en dinero y stock: `select_for_update` en ventas
      POS, ajuste de inventario, carrito/checkout, anulación, facturación y
      notas crédito (no hay oversell ni doble factura).

## 3. Frontend (Angular)

- [ ] `npm ci` limpio (lockfile `package-lock.json` versionado).
- [ ] `npm run build` con budgets activos (500 kB initial / 6 kB por estilo).
- [ ] `npm run test:ci` → Vitest en verde.
- [ ] `npm run lint` (Prettier) en verde.
- [ ] Guards de ruta: `authGuard` (sesión), `adminGuard` (ADMINISTRADOR),
      `personalGuard` (personal interno), `permisoGuard(codigo)` (permiso fino).
- [ ] Interceptor reenvía/renueva JWT automáticamente; el login valida el
      destino de `redirigir` (sin open redirect) y redirige por rol.
- [ ] El sidebar solo muestra menús según rol/permiso (no hay botones
      "invisibles" dependiendo solo del CSS).
- [ ] Errores de API mostrados con `role="alert"` y sin datos sensibles.

## 4. Despliegue (operativo)

- [ ] Servidor: Python **3.12**, Node **24**, MySQL **8.0**, migraciones
      aplicadas, `collectstatic` ejecutado (si sirves statics con Django).
- [ ] Proxy inverso con HTTPS (certificado válido + renovación automática,
      p. ej. Let's Encrypt).
- [ ] Corriendo bajo proceso supervisado (systemd/Docker) con reinicio
      automático y `Restart=on-failure`.
- [ ] Logs con rotación (ya configurada: `RotatingFileHandler`, 5 MB × 3) y
      sin excepciones sensibles; revisión periódica.
- [ ] Copias de seguridad de la BD agendadas (mysqldump) y probadas con
      restore; media/ respaldado si aplica.
- [ ] Plan de rollback: conservar el build anterior de `dist/` y backups de BD
      previos a cada release.

## 5. Accesos y operadores

- [ ] Solo `ADMINISTRADOR` gestiona usuarios, roles, cámaras, notificaciones,
      dashboard y reportes; `EMPLEADO` accede a ventas/inventario/catálogo con
      permisos finos.
- [ ] Los roles base del sistema (`ADMINISTRADOR`, `EMPLEADO`, `CLIENTE`) no
      se pueden renombrar ni borrar.
- [ ] Contraseñas con validadores de Django (fuerza mínima 8 + mayúscula +
      minúscula + número) y cambio obligatorio tras alta por personal.