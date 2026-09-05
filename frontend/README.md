# Frontend

Este directorio contiene la aplicación cliente.

## Requisitos
- **Node.js 24.x** (LTS, verificado con 24.15.0).
- **npm** 10.x/11.x (ver `packageManager` en `package.json`).
- Angular CLI 22.x (`@angular/cli` ^22.1, gestionado como devDependency).

## Instalación y ejecución
```bash
npm ci              # dependencias EXACTAS del package-lock.json (reproducible)
npm run start       # dev server en http://localhost:4200 (apunta a la API :8000)
```

## Estructura
- **src/**: Código fuente de la aplicación Angular.
- **public/**: Recursos accesibles públicamente.
- **dist/**: Archivos generados para producción.

## Comandos
- `npm run build` — build de producción (presupuestos AoT: 500 kB initial / 6 kB por componente).
- `npm run test:ci` — pruebas unitarias con Vitest (cobertura v8), 20 tests.
- `npm run test:watch` — modo interactivo.
- `npm run lint` — `prettier --check` sobre los archivos del lint.

> En CI (`..\..\README.md` → sección 5) el pipeline ejecuta
> `npm lint → npm run build → npm run test:ci` en cada push/PR.

## Calidad (Fase 6)
- **Errores Django centralizados** (`src/app/core/utils/django-error.util.ts`): todos los servicios traducen `HTTPErrorResponse` a `{codigo, detalle, errores}` con `capturarErrorDjango`, eliminando los bloques duplicados de cada servicio.
- **Timers auto-limpiables** (`src/app/core/utils/temporizador.util.ts`): `programarAviso(destroyRef, cb, ms)` cancela el `setTimeout` al destruir el componente (avisos de éxito, debounce de búsqueda, etc.).
- **Manejo de carga y error en pantallas**: señales `cargando`/`error`, bloques de error con botón **Reintentar** y estados vacíos en listados (ventas, inventario, alertas, pedidos, POS, CRUD de administración).
- **Formularios**: botones con `[disabled]` y "Guardando..." (evita doble envío).
- **Accesibilidad**: `aria-label` en buscadores, `autocomplete` en formularios, `role="alert"` en mensajes de validación y banners de error.
- **Guards y permisos**: `authGuard`, `adminGuard`, `personalGuard`, `permisoGuard(codigo)`; el sidebar ya filtra menú por rol/permiso.