import { Component, inject } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { Inclinar3dDirective } from '../../shared/directives/inclinar-3d.directive';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-dashboard',
  imports: [Inclinar3dDirective, PanelShellComponent],
  template: `
    <app-panel-shell>
      <section class="bienvenida">
        <div class="contenedor">
          <h1>Hola, {{ auth.usuario()?.nombre }}</h1>
          <p>Desde aqui administraras inventario, ventas y reportes de tu negocio.</p>
        </div>
      </section>
      <section class="contenedor modulos">
        @for (m of modulos; track m.titulo) {
          <article class="tarjeta modulo tarjeta-flot" appInclinar3d>
            <h2>{{ m.titulo }}</h2>
            <p>{{ m.texto }}</p>
            <span class="estado insignia-pulso">Proximamente</span>
          </article>
        }
      </section>
    </app-panel-shell>
  `,
  styles: [
    `

      .bienvenida {
        background: var(--primario-suave);
        padding: var(--e7) 0;
        margin-bottom: var(--e7);
      }
      .bienvenida h1 { margin: 0 0 var(--e2); font-size: clamp(26px, 5vw, 36px); }
      .bienvenida p { margin: 0; color: var(--gris); }

      .modulos {
        display: grid;
        gap: var(--e5);
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        padding-bottom: var(--e8);
      }
      .modulo h2 { margin: 0 0 var(--e2); font-size: 19px; }
      .modulo p { margin: 0 0 var(--e4); color: var(--gris); font-size: 15px; }
      .estado {
        display: inline-block;
        background: var(--primario-suave);
        color: var(--primario-osc);
        border-radius: 999px;
        padding: var(--e1) var(--e3);
        font-size: 12.5px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
    `,
  ],
})
export class DashboardComponent {
  readonly auth = inject(AuthService);

  readonly modulos = [
    { titulo: 'Inventario', texto: 'Control de stock, alertas de minimos y movimientos de producto.' },
    { titulo: 'Ventas y facturacion', texto: 'Registra ventas en el mostrador y genera la factura al instante.' },
    { titulo: 'Reportes', texto: 'Cuanto vendiste, que se mueve y que esta quieto, en un vistazo.' },
  ];
}
