/**
 * CookieBanner — aviso de cookies
 *
 * Que hace: muestra el aviso hasta que el usuario acepta, y guarda esa
 * decision en localStorage para no repetirlo en cada visita.
 * Donde se usa: montado en app.html.
 * Por que asi: el banner no bloquea la navegacion; se puede seguir mirando el
 * marketplace mientras esta abajo, que es lo que exige la practica habitual de
 * un sitio informativo.
 */

import { Component, signal } from '@angular/core';

const CLAVE = 'intersoft.cookies-aceptadas';

@Component({
  selector: 'app-cookie-banner',
  templateUrl: './cookie-banner.component.html',
  styleUrl: './cookie-banner.component.css',
})
export class CookieBannerComponent {
  readonly visible = signal(localStorage.getItem(CLAVE) !== '1');

  aceptar(): void {
    localStorage.setItem(CLAVE, '1');
    this.visible.set(false);
  }
}
