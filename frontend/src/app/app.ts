import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { WelcomeOverlayComponent } from './shared/welcome-overlay/welcome-overlay.component';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';
import { NavProgressComponent } from './shared/nav-progress/nav-progress.component';
import { TemaService } from './core/services/tema.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, WelcomeOverlayComponent, CookieBannerComponent, NavProgressComponent],
  templateUrl: './app.html',
})
export class App {
  // Instancia el servicio al arrancar para aplicar la preferencia guardada en todas las paginas
  private readonly tema = inject(TemaService);
}
