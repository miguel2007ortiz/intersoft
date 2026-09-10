/**
 * App — componente raiz que envuelve toda la aplicacion
 *
 * Que hace: es el unico componente que siempre esta montado. Su plantilla
 * (app.html) coloca la barra de progreso de navegacion, el <router-outlet>
 * donde entra cada pantalla, y los tres elementos globales: overlay de
 * bienvenida, banner de cookies y dialogo de confirmacion.
 * Donde se usa: lo monta `main.ts`.
 * Por que asi: el dialogo de confirmacion vive aqui, montado una sola vez, y
 * cualquier pantalla lo abre por medio de ConfirmacionService. Si estuviera
 * dentro de cada pantalla habria un dialogo por pantalla y se apilarian.
 */

import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { WelcomeOverlayComponent } from './shared/welcome-overlay/welcome-overlay.component';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';
import { NavProgressComponent } from './shared/nav-progress/nav-progress.component';
import { ConfirmacionComponent } from './shared/confirmacion/confirmacion.component';
import { TemaService } from './core/services/tema.service';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    WelcomeOverlayComponent,
    CookieBannerComponent,
    NavProgressComponent,
    ConfirmacionComponent,
  ],
  templateUrl: './app.html',
})
export class App {
  // Instancia el servicio al arrancar para aplicar la preferencia guardada en todas las paginas
  private readonly tema = inject(TemaService);
  private readonly auth = inject(AuthService);

  constructor() {
    // Al refrescar la pagina hay token pero los signals de permisos vuelven
    // de localStorage (pueden estar vencidos); se refrescan contra /me/.
    this.auth.cargarMe().subscribe();
  }
}
