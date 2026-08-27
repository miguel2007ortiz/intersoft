import { Component, inject, signal } from '@angular/core';
import { NavigationCancel, NavigationEnd, NavigationError, NavigationStart, Router } from '@angular/router';

@Component({
  selector: 'app-nav-progress',
  template: `
    @if (visible()) {
      <div class="barra-progreso-contenedor" [class.completa]="completa()">
        <div class="barra-progreso"></div>
      </div>
    }
  `,
  styleUrl: './nav-progress.component.css',
})
export class NavProgressComponent {
  private readonly router = inject(Router);
  readonly visible = signal(false);
  readonly completa = signal(false);
  private ocultarId?: ReturnType<typeof setTimeout>;

  constructor() {
    this.router.events.subscribe((evento) => {
      if (evento instanceof NavigationStart) {
        clearTimeout(this.ocultarId);
        this.completa.set(false);
        this.visible.set(true);
      } else if (
        evento instanceof NavigationEnd ||
        evento instanceof NavigationCancel ||
        evento instanceof NavigationError
      ) {
        this.completa.set(true);
        this.ocultarId = setTimeout(() => this.visible.set(false), 260);
      }
    });
  }
}
