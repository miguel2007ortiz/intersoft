import { Component } from '@angular/core';
import { BrilloCursorDirective } from '../../directives/brillo-cursor.directive';
import { SiteFooterComponent } from '../site-footer/site-footer.component';

/** Diseno comun de las paginas privadas: resplandor que sigue el cursor,
 * barra superior proyectada y pie armonioso. Usar asi:
 * <app-panel-shell> ...contenido... </app-panel-shell> y dentro del
 * encabezado marcarlo con el atributo panelHeader. */
@Component({
  selector: 'app-panel-shell',
  imports: [BrilloCursorDirective, SiteFooterComponent],
  template: `
    <div class="envoltorio" appBrilloCursor>
      <header class="barra">
        <div class="contenedor barra-int">
          <ng-content select="[panelHeader]" />
        </div>
      </header>

      <main class="contenido">
        <ng-content />
      </main>

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
        overflow: hidden;
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

      .barra,
      .contenido,
      app-site-footer { position: relative; z-index: 1; }

      /* Header sticky con desenfoque, igual que el de la pagina principal */
      .barra {
        position: sticky;
        top: 0;
        z-index: 500;
        background: rgba(255, 255, 255, 0.82);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--linea);
        padding: var(--e3) 0;
      }
      .barra-int {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--e4);
      }

      .contenido { flex: 1; }

      @media (max-width: 640px) {
        .barra-int { flex-wrap: wrap; }
      }
    `,
  ],
})
export class PanelShellComponent {}
