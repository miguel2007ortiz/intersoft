import { Component, HostListener, signal } from '@angular/core';
import { BrilloCursorDirective } from '../../directives/brillo-cursor.directive';
import { SiteFooterComponent } from '../site-footer/site-footer.component';
import { TopbarComponent } from '../topbar/topbar.component';
import { SidebarComponent } from '../sidebar/sidebar.component';

/** Layout comun de las paginas privadas (equivalente a un "base.html" en
 * este proyecto Angular): topbar + sidebar de navegacion + contenido de
 * altura completa + pie. Usar asi:
 * <app-panel-shell> ...contenido... </app-panel-shell>, y si la pagina
 * necesita algo extra en la cabecera, marcarlo con el atributo panelHeader
 * (se proyecta al inicio del <main>). */
@Component({
  selector: 'app-panel-shell',
  imports: [BrilloCursorDirective, SiteFooterComponent, TopbarComponent, SidebarComponent],
  template: `
    <div class="envoltorio" appBrilloCursor>
      <app-topbar [menuAbierto]="menuMovilAbierto()" (alternarMenu)="alternarMenuMovil()" />

      <div class="cuerpo">
        <app-sidebar [abierto]="menuMovilAbierto()" (cerrar)="cerrarMenuMovil()" />

        <main class="contenido">
          <ng-content select="[panelHeader]" />
          <ng-content />
        </main>
      </div>

      <app-site-footer />
    </div>
  `,
  styles: [
    `
      /* Resplandor radial que sigue el cursor (mismo efecto del login y home) */
      .envoltorio {
        min-height: 100dvh;
        display: flex;
        flex-direction: column;
        position: relative;
        overflow-x: hidden;
        --brillo-x: 50%;
        --brillo-y: 30%;
      }
      .envoltorio::before {
        content: '';
        position: absolute;
        inset: 0;
        pointer-events: none;
        background: radial-gradient(
          420px circle at var(--brillo-x) var(--brillo-y),
          rgba(38, 87, 217, 0.16),
          transparent 70%
        );
      }

      app-topbar,
      .cuerpo,
      app-site-footer { position: relative; z-index: 1; }

      /* Fila topbar / (sidebar + main) / footer, altura completa sin espacio
         muerto: .cuerpo crece para llenar lo que sobra entre topbar y footer,
         y el sidebar se estira a esa misma altura. */
      .cuerpo {
        display: flex;
        flex: 1;
        align-items: stretch;
      }

      .contenido {
        flex: 1;
        min-width: 0;
      }
    `,
  ],
})
export class PanelShellComponent {
  readonly menuMovilAbierto = signal(false);

  alternarMenuMovil(): void {
    this.menuMovilAbierto.update((abierto) => !abierto);
  }

  cerrarMenuMovil(): void {
    this.menuMovilAbierto.set(false);
  }

  @HostListener('document:keydown.escape')
  cerrarConEscape(): void {
    this.menuMovilAbierto.set(false);
  }
}
