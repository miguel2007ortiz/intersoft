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
