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
      // Fase Empleados: el middleware CambioPasswordMiddleware bloquea todo
      // con 403 salvo login/me/cambiar-password mientras haya password
      // pendiente; aqui solo redirige (esas 3 rutas nunca disparan esto).
      const esRutaCambioPassword = peticion.url.includes('/auth/cambiar-password')
        || peticion.url.includes('/auth/me');
      if (e.status === 403 && e.error?.error === 'CAMBIO_PASSWORD_REQUERIDO' && !esRutaCambioPassword) {
        router.navigate(['/cambiar-password']);
      }
      return throwError(() => e);
    }),
  );
};
