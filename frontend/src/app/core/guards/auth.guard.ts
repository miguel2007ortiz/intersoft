/**
 * authGuard — puerta del Flujo 1: exige sesion iniciada
 *
 * Que hace: deja pasar si hay token; si no, devuelve un UrlTree a /login
 * llevando la URL pedida en `?redirigir=`, para volver ahi tras iniciar sesion.
 * Donde se usa: en app.routes.ts, en toda ruta privada (es el primer guard de
 * la lista en todas ellas).
 * Por que asi: devolver UrlTree en vez de `router.navigate` deja que Angular
 * cancele la navegacion limpiamente, sin parpadeo de la pantalla protegida.
 * Importante para la exposicion: un guard NO es seguridad, es cortesia de la
 * interfaz. La seguridad real la aplica el backend en cada endpoint.
 */

import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (_ruta, estado) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.estaAutenticado()) return true;
  return router.createUrlTree(['/login'], { queryParams: { redirigir: estado.url } });
};
