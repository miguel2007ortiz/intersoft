/**
 * permisoGuard(codigo) — puerta por permiso fino, no por nombre de rol
 *
 * Que hace: es una FABRICA de guards: `permisoGuard('empleado.leer')` devuelve
 * un guard que deja pasar solo si el usuario tiene ese permiso.
 * Donde se usa: /empleados; es el patron a seguir para pantallas nuevas.
 * Por que asi: los roles los inventa el administrador en /admin/roles, asi que
 * el frontend no puede tener una lista fija de nombres de rol. Los permisos
 * llegan en /auth/me/ y son los mismos codigos que valida el backend.
 */

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
