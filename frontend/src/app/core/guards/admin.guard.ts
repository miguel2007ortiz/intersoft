/**
 * adminGuard — puerta del Flujo 3: solo ADMINISTRADOR
 *
 * Que hace: deja pasar si el usuario tiene rol ADMINISTRADOR; si no, lo
 * devuelve al panel (/dashboard) sin mostrar error.
 * Donde se usa: /admin/usuarios y /admin/roles.
 * Por que asi: se redirige en vez de mostrar "prohibido" porque el usuario no
 * llego ahi por su cuenta (el menu ni le ensena esos enlaces): si aparece, es
 * por escribir la URL a mano.
 */

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
