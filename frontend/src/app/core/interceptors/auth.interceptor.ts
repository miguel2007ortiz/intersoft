/**
 * authInterceptor — pone el token en cada peticion y renueva la sesion sola
 *
 * Que hace: tres tareas en un solo sitio:
 *   1. Anade la cabecera `Authorization: Bearer <token>` a toda peticion.
 *   2. Si el backend responde 401 y habia sesion, pide un token nuevo con el
 *      refresh y REINTENTA la peticion original; si el refresh tambien falla,
 *      cierra sesion y manda a /login?expirada=1.
 *   3. Si responde 403 con CAMBIO_PASSWORD_REQUERIDO, lleva a /cambiar-password.
 * Donde se usa: se registra una sola vez en app.config.ts y aplica a todo.
 * Por que asi: sin esto, cada servicio tendria que acordarse de poner el token
 * y de manejar el vencimiento. Aqui esta escrito una vez y no se puede olvidar.
 */

import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (peticion, siguiente) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.token();

  const esLogin = peticion.url.includes('/auth/login');
  const esRefresh = peticion.url.includes('/auth/refresh');

  const conToken =
    token && !esRefresh
      ? peticion.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : peticion;

  return siguiente(conToken).pipe(
    catchError((e: HttpErrorResponse) => {
      const eraSesionActiva = !!token;
      if (e.status === 401 && eraSesionActiva && !esLogin && !esRefresh) {
        return auth.refrescarToken().pipe(
          switchMap((renovado) => {
            if (!renovado) {
              auth.cerrarSesion();
              router.navigate(['/login'], { queryParams: { expirada: '1' } });
              return throwError(() => e);
            }
            const reintento = peticion.clone({
              setHeaders: { Authorization: `Bearer ${auth.token()}` },
            });
            return siguiente(reintento);
          }),
        );
      }
      // Fase Empleados: el middleware CambioPasswordMiddleware bloquea todo
      // con 403 salvo login/me/cambiar-password mientras haya password
      // pendiente; aqui solo redirige (esas 3 rutas nunca disparan esto).
      const esRutaCambioPassword =
        peticion.url.includes('/auth/cambiar-password') || peticion.url.includes('/auth/me');
      if (
        e.status === 403 &&
        e.error?.error === 'CAMBIO_PASSWORD_REQUERIDO' &&
        !esRutaCambioPassword
      ) {
        router.navigate(['/cambiar-password']);
      }
      return throwError(() => e);
    }),
  );
};
