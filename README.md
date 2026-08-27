# Intersoft Prueba

Este es un proyecto que incluye un backend y un frontend.

## Tecnologías utilizadas
- Python para el backend.
- Angular para el frontend.

## Configuración del entorno
- Para el backend, asegúrate de tener Python 3.x y las dependencias en `requirements.txt`.
- Para el frontend, asegúrate de tener Node.js y las dependencias en `package.json`.

## Instrucciones para ejecutar
- **Backend**: Ejecutar `python manage.py runserver`.
- **Frontend**: Ejecutar `ng serve`.

## Decisiones de arquitectura (fase 7: dashboard y reportes)
El caso de uso planteaba MongoDB para las agregaciones del dashboard, pero el
proyecto usa **MySQL**, así que todas las agregaciones (ventas diarias/mensuales,
top productos, clientes frecuentes, valor y rotación de inventario, stock bajo)
se resuelven con **vistas SQL** creadas en
`backend/core/migrations/0006_dashboard_vistas.py` y consultadas por
`backend/core/analytics.py`, filtrando siempre por `empresa_id` (multi-tenancy).
Sin dependencias externas: las gráficas del frontend son SVG puras, la exportación
de Excel es un CSV UTF-8 con BOM y la de PDF es HTML de impresión.

## Decisiones de arquitectura (fase 8: asistente IA)
El asistente IA queda disponible para **ADMINISTRADOR y EMPLEADO** (permiso
`EsPersonal`). El motor se configura por variables de entorno
(`IA_PROVIDER`, `IA_API_KEY`, `IA_API_URL`, `IA_MODEL`, `IA_TIMEOUT`,
`IA_MAX_HISTORIAL`) en `backend/intersoft/settings.py`:

- **Proveedor**: compatible con API tipo OpenAI (`IA_PROVIDER=openai` + `IA_API_KEY`).
  Sin clave configurada, usa un **mock local** (sin salida a internet) para desarrollo.
- **Contexto de negocio**: `backend/core/ia_engine.py` arma un resumen de la empresa
  (ventas, inventario, top productos, clientes frecuentes, stock bajo) reutilizando
  las vistas SQL de la fase 7 y filtrando por `empresa_id`. Nunca transmite datos
  sensibles (contraseñas, tokens, API keys).
- **Contexto de conversación**: cada sesión (`ia_conversacion`) guarda sus mensajes
  (`ia_mensaje` con rol usuario/asistente), que se reutilizan en cada llamada.
- **Fallo del motor**: ante timeout/error se devuelve `502` conservando la conversación
  (el mensaje del usuario queda guardado) para que se reintente sin duplicar.
- **Auditoría**: cada consulta y respuesta registra `IA_CONSULTA` y `IA_RESPUESTA`
  en `ActividadUsuario`.

## Decisiones de arquitectura (fase 9: monitoreo y notificaciones)
La fase 9 se compone de dos bloques: el **centro de notificaciones** (funcionalidad
viva) y el **módulo de cámaras** (entregado como *lienzo* para futuras actualizaciones).

### Centro de notificaciones (activo)
- Modelo `Notificacion` global por empresa: `tipo` (stock/factura/camara/sistema),
  `empresa`, `estado` (nueva/revisada/resuelta) y `canal` (whatsapp/email/ninguno).
  Se conserva `leida` por compatibilidad con fases anteriores.
- Servicio unificado `backend/core/notificaciones.py` (`crear_notificacion`): todas las
  fases anteriores que creaban avisos (`_notificar_admin`, `_registrar_alerta_stock`)
  fluyen por el mismo centro.
- Entrega agnóstica del proveedor en `backend/core/services/notificador.py`: WhatsApp
  Business API (`WA_*` en `settings.py`) con canal alterno por email.

**Entrega configurable por entorno (`EMAIL_*` y `WA_*` en `settings.py`):**
- **Correo**: si no se define `EMAIL_BACKEND`, en desarrollo (`DEBUG=True`) se usa el
  backend de consola y en producción el backend **SMTP** con `EMAIL_HOST/USER/PASSWORD`.
  `DEFAULT_FROM_EMAIL` es configurable.
- **WhatsApp**: requiere `WA_VINCULADO=True`, `WA_TOKEN` y el remitente `WA_NUMERO`
  (se usa como `from` en la petición a la API). Si algo falla, cae al canal email.

**Reintento (no perder el aviso):** si la entrega falla por todos los canales, la
`Notificacion` queda con `canal='ninguno'` y `entrega_pendiente=True`. Se puede reintentar:
- con el comando `python manage.py reintentar_notificaciones` (opcional `--limite N`),
- o llamando a `core.notificaciones.reintentar_entrega(aviso)` desde código.

### Módulo de cámaras (lienzo — alcance actual)
El módulo de cámaras se entrega como **base/esqueleto** para futuras actualizaciones,
no como funcionalidad terminada. Alcance actual:

- CRUD de cámaras por empresa, **solo ADMINISTRADOR** (`backend/core/views_monitoreo.py`,
  modelo `Camara` en `backend/core/models.py`).
- Campo `activa` para ocultar/mostrar una cámara del panel.
- Grabaciones históricas **no** se guardan en BD: se resuelven contra disco por
  empresa/cámara/fecha/hora en `backend/core/services/camaras.py`.

**Deudas conocidas (mejoras futuras, NO bugs a corregir en esta iteración):**
- Validar `Camara.url_stream` como URL válida (hoy es `CharField` libre).
- Paginar resultados y validar el filtro `activas` en `CamarasView.get`.
- Definir reproducción/servicio de streaming real del video en vivo.
