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
