/**
 * app.config.ts — arranque de la aplicacion (proveedores raiz)
 *
 * Que hace: registra en un solo sitio todo lo que la app necesita desde el
 * primer milisegundo: el Router con la tabla de rutas, el HttpClient con el
 * interceptor de sesion y el idioma es-CO.
 * Donde se usa: lo consume `main.ts` en `bootstrapApplication(App, appConfig)`.
 * Por que asi: Angular 22 sin NgModule. `withComponentInputBinding()` deja que
 * un componente reciba los parametros de la URL como `input()`, sin inyectar
 * ActivatedRoute. El LOCALE_ID es-CO es lo que hace que los precios se pinten
 * 50.000 y no 50,000 en toda la aplicacion.
 */

import { ApplicationConfig, LOCALE_ID } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';
import localeEsCO from '@angular/common/locales/es-CO';
import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';

registerLocaleData(localeEsCO, 'es-CO');

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withInterceptors([authInterceptor])),
    // Formato numerico de Colombia (es-CO): miles con punto (50.000), decimales con coma.
    { provide: LOCALE_ID, useValue: 'es-CO' },
  ],
};
