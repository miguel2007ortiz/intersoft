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

  const conToken = token && !esRefresh
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
      return throwError(() => e);
    }),
  );
};