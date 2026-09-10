/**
 * personalGuard — puerta del Flujo 2: personal de la tienda, no clientes
 *
 * Que hace: deja pasar a cualquier rol que NO sea CLIENTE (administrador,
 * empleado y roles propios); al cliente lo manda al marketplace.
 * Donde se usa: clientes, productos, POS, ventas, inventario, alertas.
 * Por que asi: la pregunta correcta aqui es "trabaja en la tienda?", no "que
 * rol exacto tiene?". Asi un rol nuevo creado por el administrador funciona
 * sin tocar este archivo.
 */

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
