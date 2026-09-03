# Riesgos — InterSoft (resumido al cierre)

Estado al cierre de la entrega. **Resueltos** = verificados por código y/o
pruebas (241 backend + 20 frontend). **Pendientes** = mejoras/deudas conocidas,
ninguna es un bug critico abierto que bloquee la entrega.

---

## Riesgos resueltos

### Backend
| Riesgo | Resolución |
|---|---|
| Oversell de stock en ventas POS | Un solo `transaction.atomic()` con `select_for_update` (lock + chequeo + movimiento); `ConcurrenciaPOS` con threads confirma que nunca sobrevende. |
| Doble checkout del mismo carrito | Carrito y productos bloqueados con `select_for_update`; checkout serializado por comprador. |
| Doble FacturaElectronica por venta | Venta bloqueada + OneToOne; respaldo `IntegrityError` → `YA_FACTURADA`. |
| Nota crédito inconsistente (descuadre de stock) | Venta bloqueada y flujo (crear+enviar+revertir) atómico. |
| Anulación fuera de transaccion | Locks de venta y productos movidos **dentro** del `atomic`. |
| Ajuste de inventario perdía el lock | `select_for_update` dentro del `atomic` (antes se liberaba al salir). |
| Correlativo `numero_factura` duplicado | Fila de `Empresa` bloqueada para serializar el consecutivo. |
| Grafo de migraciones con dos ramas `0010` | Merge `core/0014` (vacío) + índices aditivos `0015`; `makemigrations --check --dry-run` limpio; suite verde desde cero. |
| Errores de API con shapes inconsistentes / con tracebacks | Manejador global (`core/exceptions.py`): siempre `{codigo, detalle, errores}`, sin trazas ni datos sensibles. |
| Entradas no validadas (fechas, precios, `categoria`) | Validación estricta en ventas/dashboard/reportes/catálogo → 400 uniforme. |
| `url_stream` inyectable (`javascript:`, etc.) | Solo `http(s)`, `rtsp`, `rtmp`; vacío permitido (cámara sin video). |
| Listados sin tope (DoS por filas) | Paginación acotada a 200 (default 50) en productos, usuarios, pedidos, inventario. |
| Login por fuerza bruta | Bloqueo tras 5 intentos (`MAX_INTENTOS_LOGIN`) por 15 min (`MINUTOS_BLOQUEO`). |
| Fuga multi-tenant por `Rol` global (hallazgo AUDITORIA) | `Rol.empresa` (FK) + unicidad por empresa + `roles_visibles()`; pruebas de aislamiento entre empresas (roles no se ven/clonan/asignan transfrontera). |
| Config insegura en producción | Fail-fast: sin `SECRET_KEY` real o con `ALLOWED_HOSTS=*` la app **no arranca** con `DEBUG=False`; cookies/HSTS/HTTPS se endurecen solas. |
| Reset de password con token eterno | Tokens expiran (30 min); pruebas con token expirado/inexistente. |
| N+1 en listados | Optimización de consultas eliminando `select_related`/`prefetch_related` faltantes. |

### Frontend
| Riesgo | Resolución |
|---|---|
| Guard de rutas por rol incompleto | Guards `auth`, `admin`, `personal`, `permiso(codigo)` + sidebar que filtra menú; cobertura de tests. |
| Open redirect tras login | Destino `redirigir` validado (solo rutas locales). |
| JWT vencido durante el uso | Interceptor renueva el token automáticamente (flujo refresh). |
| Errores de API duplicados/incoherentes en 7 servicios | Helper compartido `capturarErrorDjango` (`core/utils/django-error.util.ts`). |
| Silenciar errores de carga / sin reintento | Señales de error + botón "Reintentar" + estados vacíos en todos los listados. |
| Doble envío en formularios | `guardando` + `[disabled]` + "Guardando..." en CRUD y carga de datos. |
| Fugas de `setTimeout`/debounce al destruir | `programarAviso(destroyRef, ...)` + `ngOnDestroy` en componentes con timers. |
| Accesibilidad de errores | `role="alert"` en 39 mensajes de validación + banners; `aria-label` en buscadores; `autocomplete` en formularios. |
| Bundle fuera de presupuesto | `ng build` con budgets (500 kB initial / 6 kB por estilo) — pasa en 311 kB. |

### Entrega / repo
| Riesgo | Resolución |
|---|---|
| Codificación/line endings inconsistentes | Verificado: todos los textos del repo UTF-8 sin BOM; `.editorconfig` raíz + `.gitattributes` (LF en git, CRLF solo en `.bat`). |
| Dependencias backend no reproducibles | `requirements.txt` con versiones **exactas** (`==`) verificadas (241 tests). Frontend con `package-lock.json` + `npm ci`. |
| Sin regresión automática | Pipeline CI (`.github/workflows/ci.yml`): build Angular + tests frontend + `django check` + migraciones pendientes + suite backend sobre MySQL 8. |
| Secretos, builds, media, logs en git | `.gitignore` raíz actualizado y verificado (`git check-ignore` ok / `git ls-files` sin `.env` ni claves). |

---

## Riesgos pendientes (mejoras conocidas, no bloqueantes)

1. **Throttling por IP**: solo hay bloqueo por cuenta (login). No hay
   `DRF throttles` por IP en endpoints sensibles (refresh, recuperación,
   creación de cuenta). Recomendado antes de exponer a internet.
2. **Módulo de cámaras**: es un "lienzo" deliberado — no hay streaming en
   vivo, no hay paginación en `CamarasView`, y las grabaciones se resuelven
   contra disco (sin BD). El campo `url_stream` ya valida protocolo
   (fase 5), pero el alcance completo de video queda para una iteración
   posterior.
3. **Sin CSP en cabeceras**: el backend no emite `Content-Security-Policy`
   (sí `X-FRAME_OPTIONS=DENY` y HSTS). Añadir CSP en nginx mitigaría XSS
   defensivamente.
4. **Sin e2e del frontend**: la cobertura es unitaria (guard, interceptor,
   servicios, componentes clave). Un e2e (Playwright) sobre happy path
   (login → venta → check) cerraría el ciclo.
5. **Volumen de datos**: vistas SQL y agregaciones del dashboard están
   optimizadas para el volumen actual; para volumen alto convendría
   materializar/archivar ventas viejas.
6. **Media en disco local**: `MEDIA_ROOT` local; en multi-servidor se
   recomienda almacenar en object storage.
7. **Backups y monitoring**: son operativos, no implementados en la app.
   El checklist de despliegue (`docs/CHECKLIST-SEGURIDAD.md`,
   `docs/DESPLIEGUE.md`) los exige como paso manual/agendado.

> Documentación cruzada: requisitos e instalación en `README.md` raíz;
> especificos de backend en `backend/README.md`; calidad frontend en
> `frontend/README.md`; seguridad y despliegue en `docs/`.