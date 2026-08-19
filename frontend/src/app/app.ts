import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { WelcomeOverlayComponent } from './shared/welcome-overlay/welcome-overlay.component';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, WelcomeOverlayComponent, CookieBannerComponent],
  templateUrl: './app.html',
})
export class App {}
