import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Fase Empleados: guard por permiso fino (no por nombre de rol), para
 * rutas cuyo acceso depende de /api/auth/me/ -> permisos. No reemplaza a
 * auth/admin/personal.guard, que siguen intactos para lo que ya usaban. */
export function permisoGuard(codigo: string): CanActivateFn {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    if (auth.tienePermiso(codigo)) return true;
    return router.createUrlTree(['/dashboard']);
  };
}
