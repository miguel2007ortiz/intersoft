import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { WelcomeOverlayComponent } from './shared/welcome-overlay/welcome-overlay.component';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';
import { NavProgressComponent } from './shared/nav-progress/nav-progress.component';
import { TemaService } from './core/services/tema.service';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, WelcomeOverlayComponent, CookieBannerComponent, NavProgressComponent],
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
