# InterSoft — Roadmap de mejoras

Priorizado por valor/esfuerzo. Referencias a archivos reales del repo (`backend/` y `frontend/`).

---

## Fase A — Estabilidad y calidad de datos

### A1. Integridad financiera: validar `Venta.total` vs suma de `DetalleVenta` **(hecho)**
- **Dónde**: `backend/core/models.py` (`Venta`, `DetalleVenta`) y `backend/core/signals.py`.
- **Qué**: `recalcular_totales_venta` (señal `mantener_totales_venta`, `post_save`/`post_delete`
  de `DetalleVenta`) reconstruye `subtotal`/`total` = suma de `cantidad * precio_unitario` en un
  único `UPDATE` vía `Subquery` (evita snapshot stale de MySQL REPEATABLE READ); borrado de línea
  siempre por instancia (queryset batch no dispara post_delete). Validación de entrada:
  `VentaPOSView` rechaza `descuento > subtotal` (`DESCUENTO_INVALIDO`) y el `CuponSerializer`
  limita `porcentaje` a 0-100.
- **Decisión registrada**: `descuento > subtotal` NO es rechazo estricto a nivel de BD; la señal
  aplana `total` a 0 (clamp) conservando el descuento. Garantizar `descuento <= subtotal` como
  `CheckConstraint` exigiría cambiar ese comportamiento (ver `tests_integridad.py`,
  `test_descuento_mayor_al_subtotal_total_queda_en_cero`).
- **Tests**: `backend/core/tests_integridad.py` (crear/eliminar/sin detalles, descuento preservado,
  clamp, invocación manual).

### A2. Estados vacíos y manejo de errores en el panel interno **(hecho)**
- **Dónde**: componentes del panel (`clientes`, `productos`, `ventas`, `pedidos`,
  `envios`, tienda).
- **Qué**: unificar componente de "estado vacío" (sin resultados) y de "error" con reintento,
  consistente con la tienda (`app-estado-vacio`, tipos `vacio|busqueda|error`,
  `frontend/src/app/shared/estado-vacio/`). Ventas/tienda/envios ya lo tenían; se completó
  `clientes` y `productos`: el fallo de carga ya no muestra el falso vacío "Todavía no hay X"
  sino `<app-estado-vacio tipo="error">` con Reintentar (señal `errorCarga` separada del `error`
  de formularios), y `productos` gana el estado "Sin resultados" para búsqueda/filtro con
  acción "Limpiar filtros" (`limpiarFiltros()`).
- **Tests**: `clientes.component.spec.ts` y `productos.component.spec.ts` (error de carga +
  reintento que recarga, vacío inicial, sin resultados de búsqueda/filtro).

### A3. Aislamiento de datos de demo **(hecho)**
- **Dónde**: management commands de seed + datos de prueba sembrados durante desarrollo.
- **Qué**: todo seed de demostración vive en commands — `seed_demo`
  (`backend/core/management/commands/seed_demo.py`, data de negocio demo) y
  `seed_masivo` (`--cantidad`, `--nit`, volumen para catalog/pos/dashboard).
  Ninguna migración siembra datos demo (solo `cuentas/0003_seed_rbac` siembra los roles
  base del sistema, bootstrap funcional — no demo, y su edición está vedada por invariante).
  **Flag anti-producción**: `seed_demo` y `seed_masivo` abortan con `CommandError`
  si `DEBUG=False`; `--force` los habilita solo con riesgo asumido.
- **Tests**: `backend/core/tests_seed.py` (guards de producción para ambos commands,
  `--force` y `DEBUG=True`).

---

## Fase B — Rendimiento
- **B1. Caché (Redis o DB)**: `settings.py` sin `CACHES`. Cachear dashboard/tarjetas de
  `analytics.py`, contexto de IA y catálogo. TTL 60-300s, invalidar al crear ventas/productos.
- **B2. Paginación en el catálogo público **(hecho)**: `CatalogoPublicoView`
  (`backend/core/views_tienda.py`) filtra/ordena sin cortar página: devuelve
  `pagina`/`por_pagina` (24)/`total` (conteo real del filtro)/`total_paginas`,
  página inválida cae a 1, y cachea 60s por clave que incluye filtros+orden+página.
  Frente (`frontend/src/app/features/tienda/catalogo/`) con **paginador por botones**
  (Anterior/Siguiente + "Página X de Y", vuelve a página 1 en cada búsqueda/filtro),
  en vez de infinite scroll: decisión tomada porque el catálogo público ya está
  cacheado (60s) y el grid de 24 permite navegación predecible; el scroll infinito
  encaja mejor con datos mutando rápido y sin paginador, no es el caso aquí.
  Tests: `backend/core/tests_fase5.py` (corte a 24, total real, sin duplicados entre
  páginas, página inválida) y `frontend/src/app/core/services/tienda.service.spec.ts`
  (envía `pagina` y lee `total_paginas`).

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
- **F2. Panel de envíos (frontend, hecho)**: seguimiento de despacho en el
  historial del comprador (`features/tienda/pedidos`) + panel de gestión para
  personal interno (`features/envios`, ruta `/envios` con `personalGuard` y
  enlace en el sidebar): cola filtrable por estado y modal para cambiar
  transportadora, guía, fecha estimada, notas y estado (solo transiciones
  válidas, validadas por el backend). Servicio `core/services/envios.service.ts`
  (`listarEnvios`, `obtenerEnvio`, `actualizarEnvio`). Tests Vitest del panel,
  servicio, pedidos y sidebar + e2e Playwright (`npm run test:e2e`, 2/2).

---

## Matriz de prioridad (impacto vs esfuerzo)
| Ítem | Impacto | Esfuerzo | Prioridad |
|------|---------|----------|-----------|
| A1 Integridad financiera | Alto | Bajo | — (hecho) |
| B2 Paginación catálogo | Alto | Bajo | — (hecho) |
| E2 PDF/XML comprobantes | Medio | Bajo | 3 |
| B1 Caché | Alto | Medio | 4 |
| C2 CI endurecido | Medio | Medio | 5 |
| A2 Estados vacíos | Medio | Bajo | — (hecho) |
| C1 Docker | Medio-Alto | Medio | 7 |
| A3 Aislamiento demo | Medio | Bajo | — (hecho) |
| E1 Design system | Medio | Medio | 9 |
| D1 DIAN real | Alto | Alto | 10 |
| D2 IA real | Alto | Alto | 11 |
| F1 Envíos backend | Alto | Medio | — (hecho) |
| F2 Envíos frontend | Alto | Bajo | — (hecho) |

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