import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Fase 3: clientes y productos son del personal interno
 * (ADMINISTRADOR o EMPLEADO); el rol CLIENTE no entra. */
export const personalGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const rol = auth.usuario()?.rol;
  if (rol === 'ADMINISTRADOR' || rol === 'EMPLEADO') return true;
  return router.createUrlTree(['/dashboard']);
};
