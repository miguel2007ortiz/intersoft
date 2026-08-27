import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (peticion, siguiente) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.token();

  const conToken = token
    ? peticion.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : peticion;

  return siguiente(conToken).pipe(
    catchError((e: HttpErrorResponse) => {
      const eraSesionActiva = !!token;
      const esLogin = peticion.url.includes('/auth/login');
      if (e.status === 401 && eraSesionActiva && !esLogin) {
        auth.cerrarSesion();
        router.navigate(['/login'], { queryParams: { expirada: '1' } });
      }
      return throwError(() => e);
    }),
  );
};
