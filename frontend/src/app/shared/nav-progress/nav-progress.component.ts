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
