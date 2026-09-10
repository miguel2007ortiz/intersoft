/**
 * WelcomeOverlay — saludo a pantalla completa tras iniciar sesion
 *
 * Que hace: dibuja el "Hola, <nombre>" que enciende WelcomeService durante
 * 2,4 segundos.
 * Donde se usa: montado en app.html.
 * Por que asi: vive en la raiz y no dentro del login, porque el saludo debe
 * seguir en pantalla mientras el Router ya esta pintando el panel.
 */

import { Component, inject } from '@angular/core';
import { WelcomeService } from '../../core/services/welcome.service';

@Component({
  selector: 'app-welcome-overlay',
  templateUrl: './welcome-overlay.component.html',
  styleUrl: './welcome-overlay.component.css',
})
export class WelcomeOverlayComponent {
  readonly welcome = inject(WelcomeService);

  /** "Daniel Velasco Ruiz" -> "Daniel" */
  primerNombre(nombre: string): string {
    return (nombre ?? '').trim().split(' ')[0] || 'Bienvenido';
  }

  cerrar(): void {
    this.welcome.ocultar();
  }
}
