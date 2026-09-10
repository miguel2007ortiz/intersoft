/**
 * NavProgress — barra fina de progreso al cambiar de pantalla
 *
 * Que hace: escucha los eventos del Router y muestra una barra arriba
 * mientras se descarga el codigo de la pantalla destino.
 * Donde se usa: montado en app.html, siempre visible.
 * Por que asi: como las rutas cargan su codigo bajo demanda (loadComponent),
 * puede haber un instante sin nada en pantalla; esta barra da la senal de que
 * la aplicacion esta trabajando y no colgada.
 */

import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  NavigationCancel,
  NavigationEnd,
  NavigationError,
  NavigationStart,
  Router,
} from '@angular/router';

@Component({
  selector: 'app-nav-progress',
  templateUrl: './nav-progress.component.html',
  styleUrl: './nav-progress.component.css',
})
export class NavProgressComponent {
  private readonly router = inject(Router);
  readonly visible = signal(false);
  readonly completa = signal(false);
  private ocultarId?: ReturnType<typeof setTimeout>;

  constructor() {
    this.router.events.pipe(takeUntilDestroyed()).subscribe((evento) => {
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
