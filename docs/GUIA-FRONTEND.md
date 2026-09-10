# Guía del frontend — mapa para exponer

Documento de orientación: dónde está cada cosa, por qué está ahí y qué decir
de cada pieza. Todos los archivos `.ts` de `frontend/src/app` empiezan con una
cabecera `Qué hace / Dónde se usa / Por qué así`; este documento es el índice
que las une.

## 1. Cómo arranca la aplicación

| Archivo | Papel |
|---|---|
| `src/main.ts` | Monta el componente raíz. |
| `src/app/app.config.ts` | Proveedores globales: Router, HttpClient con interceptor, idioma `es-CO`. |
| `src/app/app.routes.ts` | Tabla de rutas: URL, título, guards y componente. |
| `src/app/app.ts` + `app.html` | Único componente siempre montado: barra de progreso, `<router-outlet>`, overlay de bienvenida, banner de cookies y diálogo de confirmación. |

Angular 22 **standalone**: no hay `NgModule`. Cada componente declara sus
propios `imports` y las rutas cargan el código bajo demanda con
`loadComponent`, así el navegador solo descarga la pantalla que se visita.

## 2. Los tres flujos y quién entra a cada uno

La protección se lee de un vistazo en `app.routes.ts`.

**Público (sin guard):** `/` y `/catalogo` (marketplace), `/login`,
`/registro`, `/registro-comprador`, `/recuperar`, `/restablecer`.

**Flujo 1 — sesión (`authGuard`):** `/dashboard`, `/configuracion`,
`/cambiar-password`, `/carrito`, `/checkout`, `/pago/retorno`, `/pedidos`,
`/favoritos`.

**Flujo 2 — operación de la tienda (`personalGuard`, o permiso concreto):**
`/clientes`, `/productos`, `/pos`, `/ventas`, `/inventario`, `/alertas`,
`/facturacion`, `/ia`, y `/empleados` con `permisoGuard('empleado.leer')`.

**Flujo 3 — administración (`adminGuard`):** `/admin/usuarios`,
`/admin/roles`, `/reportes`, `/monitoreo/camaras`,
`/monitoreo/notificaciones`.

Cualquier URL desconocida cae en `{ path: '**' }` y va al marketplace.

> Frase clave para la exposición: **un guard no es seguridad, es cortesía de
> la interfaz.** Evita que alguien llegue a una pantalla que no le sirve. La
> seguridad real la aplica el backend en cada endpoint; por eso el mismo
> permiso se comprueba en los dos lados.

## 3. Sesión: cómo se sostiene

- `core/services/auth.service.ts` es el dueño único de la sesión. Guarda
  token, refresh, usuario y permisos en **signals**, y los persiste en
  `localStorage` bajo las claves `intersoft.*`, por eso la sesión sobrevive a
  F5. Al arrancar revalida contra `/auth/me/` por si la cuenta se desactivó.
- `core/interceptors/auth.interceptor.ts` hace tres cosas para toda la app:
  1. pone `Authorization: Bearer <token>` en cada petición;
  2. ante un **401**, pide un token nuevo con el refresh y reintenta la
     petición original; si el refresh también falla, cierra sesión y va a
     `/login?expirada=1`;
  3. ante un **403 CAMBIO_PASSWORD_REQUERIDO**, lleva a `/cambiar-password`.
- Si diez peticiones caducan a la vez se pide **un solo** token nuevo (una
  promesa compartida), no diez.

## 4. Permisos: por qué no basta con el rol

El administrador crea sus propios roles en `/admin/roles` y les marca
permisos de un catálogo que devuelve el backend (`empleado.leer`,
`venta.anular`, …). Por eso el frontend **no** tiene una lista fija de nombres
de rol: `permisoGuard('empleado.leer')` pregunta por el permiso, que llega en
`/auth/me/` y es el mismo código que valida el backend. Un rol nuevo funciona
sin tocar el frontend.

## 5. Estructura de carpetas

```
src/app/
  core/          lo transversal, sin pantalla propia
    guards/        auth, personal, admin, permiso
    interceptors/  auth.interceptor
    services/      una API por área (auth, tienda, catalogo, seguridad, ...)
    models/        los tipos = contrato con el backend
    validators/    reglas de formulario (email único, contraseña)
    utils/         errores de Django, temporizadores, pasarela
  shared/        piezas reutilizables (layout, diálogo, estado vacío, directivas)
  features/      una carpeta por pantalla
```

Regla: `features/` **nunca** llama a `HttpClient` directamente; siempre pasa
por un servicio de `core/services/`. Así una pantalla se puede probar con un
servicio falso y el manejo de errores está escrito una sola vez.

## 6. Decisiones que conviene poder defender

- **Signals en vez de RxJS para el estado de pantalla.** La vista se repinta
  sola al cambiar el valor y no hay suscripciones que olvidar cerrar. RxJS se
  sigue usando donde encaja: las peticiones HTTP.
- **La paginación y los totales los calcula el backend.** El frontend nunca
  descarga la tabla entera ni suma precios por su cuenta: el total que ve el
  cliente es exactamente el que se va a cobrar.
- **Diálogo de confirmación propio** (`ConfirmacionService` +
  `shared/confirmacion`) en lugar de `confirm()`: el nativo bloquea el hilo,
  no se puede estilizar, ignora el modo noche y algunos navegadores lo
  suprimen, dejando el clic sin respuesta. El nuestro atrapa el foco, cierra
  con Escape y lo devuelve al botón que lo abrió.
- **Un solo traductor de errores** (`capturarErrorDjango`): sustituyó a siete
  implementaciones parecidas. El mismo fallo se ve igual en todas las
  pantallas.
- **Temporizadores atados al `DestroyRef`** (`programarAviso`): imposible
  dejar un `setTimeout` escribiendo en un componente ya destruido.
- **El resultado del pago se confirma contra el backend**, no se cree lo que
  diga la URL de retorno de la pasarela. Si no, bastaría con escribir a mano
  una URL de «aprobado» para dar un pedido por pagado.
- **`LOCALE_ID: 'es-CO'`** es lo que hace que los precios se pinten `50.000`
  y no `50,000` en toda la aplicación.

## 7. Detalle útil si preguntan por un bug real

**Síntoma:** los favoritos aparecían y desaparecían al segundo.
**Causa:** la tarjeta de `/favoritos` declaraba su propia
`animation: entrar … backwards`, que pisaba a la animación de la clase global
`.aparecer`. Al terminar, la tarjeta volvía al `opacity: 0` de base de la
clase global y se hacía invisible — los datos estaban ahí, en el DOM.
**Arreglo:** quitar la animación del componente y dejar solo la global, que
termina en `opacity: 1` (`forwards`).
**Lección:** `innerText` no delata un elemento invisible; hay que mirar
`getComputedStyle`.

## 8. Comprobar que todo está bien

```bash
cd frontend
npx ng build --configuration development   # compila
npx ng build                               # build de producción
npx ng test --configuration ci             # pruebas (vitest)
npm run lint                               # formato (prettier)
```

`npx vitest run` **no** funciona por sí solo (falla la compilación JIT): hay
que usar `ng test`, que aplica la configuración de Angular.
