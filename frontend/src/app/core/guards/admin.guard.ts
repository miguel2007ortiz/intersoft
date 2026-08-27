import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Fase 2: las pantallas de seguridad solo las ve el ADMINISTRADOR. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.esAdministrador()) return true;
  return router.createUrlTree(['/dashboard']);
};
