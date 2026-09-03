# InterSoft — Roadmap de mejoras

Priorizado por valor/esfuerzo. Referencias a archivos reales del repo (`backend/` y `frontend/`).

---

## Fase A — Estabilidad y calidad de datos

### A1. Integridad financiera: validar `Venta.total` vs suma de `DetalleVenta`
- **Dónde**: `backend/core/models.py` (`Venta`, `DetalleVenta`) y señales en `core/signals.py`.
- **Qué**: `DetalleVenta.subtotal` ya es property calculada (buen patrón). Falta garantizar que
  `Venta.total == sum(detalle.subtotal)` tras guardar/editar y que `descuento <= subtotal`.
  Señal `post_save`/`post_delete` en `DetalleVenta` que recalcula y persiste el total de la venta padre.
- **Beneficio**: evita facturas/pedidos con totales inconsistentes (crítico para reportes y DIAN).

### A2. Estados vacíos y manejo de errores en el panel interno
- **Dónde**: componentes del panel (`clientes`, `productos`, `ventas`, `pedidos`).
- **Qué**: unificar componente de "estado vacío" (sin resultados) y de "error" con reintento,
  consistente con la tienda.

### A3. Aislamiento de datos de demo
- **Dónde**: management commands de seed + datos de prueba sembrados durante desarrollo.
- **Qué**: meter todo seed de demostración en management commands (`seed_demo`) y **no** en
  migraciones; flag para no correr en producción.

---

## Fase B — Rendimiento
- **B1. Caché (Redis o DB)**: `settings.py` sin `CACHES`. Cachear dashboard/tarjetas de
  `analytics.py`, contexto de IA y catálogo. TTL 60-300s, invalidar al crear ventas/productos.
- **B2. Paginación en el catálogo público**: `CatalogoPublicoView` (views_tienda.py) filtra/ordena
  sin cortar página. Añadir `pagina`/`por_pagina` + `total`; frente con infinite scroll.

---

## Fase C — Ingeniería / DevOps
- **C1. Docker**: no hay `Dockerfile`/`docker-compose`. Añadir `docker-compose`
  (MySQL 8 + backend Py3.12 + frontend Node 22 [+ Redis para B1]).
- **C2. Endurecer CI**: gate de cobertura mínima, `ruff`/`bandit` para Python y `npm audit`.

---

## Fase D — Integraciones reales
- **D1. Facturación electrónica DIAN real**: el adaptador (`services/dian_adapter.py`) genera
  comprobantes reales (PDF con `reportlab`, XML con `lxml`) y CUFE SHA-384, y hay un cliente SOAP
  1.2 (`zeep`) detrás de `DIAN_MOCK=False`. Con `DIAN_MOCK=True` (default) aprueba localmente.
  **Hecho**: el mock/simulación produce PDF/XML y CUFE reales; la llamada al Web Service real queda
  implementada y configurable (`DIAN_WSDL`/`DIAN_USUARIO`/`DIAN_CLAVE`), pero solo es verificable
  con la habilitación oficial + certificado (firma XAdES-EPES pendiente de credenciales). Tests en
  `core/tests_dian.py` (19).
- **D2. IA con proveedor real**: `ia_engine.py` cae a `_mock` sin `IA_API_KEY`. Definir prompt de
  sistema con contexto de empresa + rate-limit y timeout con fallback.

---

## Fase E — Calidad de producto
- **E1. Design system vivo**: tokens de `styles.css` + capturas `figma-marketplace/` → documentar
  el sistema (colores, tipografía, componentes de tienda). **Hecho** → `docs/DESIGN_SYSTEM.md`.
- **E2. Validar descarga de PDF/XML** de facturas y notas crédito en todos los casos (tests e2e). **Hecho**.

---

## Fase F — Envíos (despachos del marketplace)
- **F1. Módulo de envíos (backend, hecho)**: modelo `Envio` (1:1 con `Venta`,
  solo canal marketplace), máquina de estados
  (`pendiente/preparando/despachado/en_transito/entregado/no_entregado/devuelto`),
  `CheckoutView` exige dirección/ciudad del cliente (`SIN_DIRECCION_ENVIO`) y
  crea el envío al facturar. API de gestión (`/api/envios/`,
  `/api/ventas/<id>/envio/`, `EsPersonal`, aislada por empresa) y de
  seguimiento para el comprador (`/api/tienda/pedidos/` incluye `envio`).
  Tests en `core/tests.py` (`EnvioCreacionTest`, `EnvioGestionTest`).
- **F2. Panel de envíos (frontend, pendiente)**: vista de seguimiento en el
  historial de pedidos del comprador + panel de gestión para personal
  interno (lista filtrable + cambio de estado/transportadora/guía). Detalle
  de la tarea en `AGENTS.md` §6.2.

---

## Matriz de prioridad (impacto vs esfuerzo)
| Ítem | Impacto | Esfuerzo | Prioridad |
|------|---------|----------|-----------|
| A1 Integridad financiera | Alto | Bajo | 1 |
| B2 Paginación catálogo | Alto | Bajo | 2 |
| E2 PDF/XML comprobantes | Medio | Bajo | 3 |
| B1 Caché | Alto | Medio | 4 |
| C2 CI endurecido | Medio | Medio | 5 |
| A2 Estados vacíos | Medio | Bajo | 6 |
| C1 Docker | Medio-Alto | Medio | 7 |
| A3 Aislamiento demo | Medio | Bajo | 8 |
| E1 Design system | Medio | Medio | 9 |
| D1 DIAN real | Alto | Alto | 10 |
| D2 IA real | Alto | Alto | 11 |
| F1 Envíos backend | Alto | Medio | — (hecho) |
| F2 Envíos frontend | Alto | Bajo | 12 |

---

## Decisiones abiertas / resueltas
- **cache de DB (resuelta)**: B1 usa `DatabaseCache` (tabla `intersoft_cache`) por defecto, sin
  infraestructura extra; se puede apuntar a Redis con `CACHE_BACKEND`/`CACHE_LOCATION`. En tests se
  usa `LocMemCache`.
- **Paginación de catálogo (resuelta)**: B2 mantiene paginador clásico (Anterior/Siguiente); el
  backend ya devuelve `pagina/por_pagina/total_paginas`.
- **Proveedor de IA**: `openai` vs `groq` (configurable por `IA_PROVIDER`).
- **Alcance de Docker**: solo dev vs incluir producción/nginx.
- **C2 CI endurecido (resuelta)**: se añadió al workflow `.github/workflows/ci.yml` un paso de
  `npm audit` (frontend); y en el job backend: `ruff check`, `bandit` (con `backend/bandit.yaml`
  donde se justifican los falsos positivos B608/B310/B311/B105-B107) y cobertura mínima del 70%
  con `coverage --fail-under=70` sobre el suite `core`. Herramientas en `backend/requirements-dev.txt`.
- **C1 Docker (resuelta)**: `backend/Dockerfile` (Py 3.12 + Gunicorn), `frontend/Dockerfile`
  (multi-stage Node 22 -> nginx con reverse proxy de `/api` y `/media`), `docker-compose.yml` con
  MySQL 8, Redis (listo para B1) y ambos servicios. El frontend inyecta `apiUrl` en build vía
  `--build-arg API_URL` (default relativo `/api`).
- **D2 IA con contexto (resuelta)**: el prompt de sistema ahora inyecta el contexto de negocio
  (`ia_engine._system_prompt`) y hay rate-limit por usuario del chat
  (`IA_MAX_PETICIONES`/`IA_PETICIONES_VENTANA`, default 15 en 60s) con respuesta 429.
- **E2 descarga de PDF/XML (resuelta)**: se añadieron tests (`core/tests_fase5.py`,
  clase `DescargaComprobantesTest`) que validan que la factura y la nota crédito aprobadas
  exponen URLs `/media/...` de su PDF/XML, que el archivo existe en disco con su contenido, y que
  un comprobante no aprobado no expone nada descargable.
- **E1 design system vivo (resuelta)**: documento `docs/DESIGN_SYSTEM.md` con los tokens reales de
  `frontend/src/styles.css` (colores claro/noche, espaciado, radios, sombras, tipografía),
  componentes reutilizables y referencia a `figma-marketplace/` (tokens + capturas, no versionado).
- **D1 DIAN real (resuelta)**: el adaptador quedó con comprobantes reales (PDF con `reportlab`,
  XML con `lxml`, CUFE SHA-384 determinista) y un cliente SOAP 1.2 con `zeep` activable con
  `DIAN_MOCK=False` y credenciales `DIAN_WSDL`/`DIAN_USUARIO`/`DIAN_CLAVE`. `_guardar_comprobantes`
  ahora acepta PDF en `bytes`. Se añadieron 19 tests (`core/tests_dian.py`) y librerías a
  `requirements.txt`. La firma XAdES y la transmisión asíncrona "EN PROCESO" quedan documentadas
  como pendientes de la habilitación oficial.