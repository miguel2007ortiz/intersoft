import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-configuracion',
  imports: [RouterLink, PanelShellComponent],
  template: `
    <app-panel-shell>
      <span panelHeader class="logo">Inter<span class="acento">Soft</span></span>
      <a panelHeader routerLink="/dashboard" class="volver">&larr; Volver al panel</a>

      <section class="contenedor seccion">
        <div class="tarjeta">
          <h1>Configuracion</h1>
          <p class="descripcion">Informacion de tu cuenta y de la empresa.</p>
          <dl>
            <div class="fila"><dt>Nombre</dt><dd>{{ auth.usuario()?.nombre }}</dd></div>
            <div class="fila"><dt>Correo</dt><dd>{{ auth.usuario()?.email }}</dd></div>
            <div class="fila"><dt>Rol</dt><dd>{{ auth.usuario()?.rol }}</dd></div>
            <div class="fila"><dt>Empresa</dt><dd>{{ auth.usuario()?.empresa }}</dd></div>
          </dl>
          <p class="nota">Mas opciones de configuracion disponibles proximamente.</p>
        </div>
      </section>
    </app-panel-shell>
  `,
  styles: [
    `
      .logo { font-size: 22px; font-weight: 700; }
      .acento { color: var(--primario); }
      .volver { color: var(--primario); text-decoration: none; font-weight: 600; font-size: 14.5px; }
      .volver:hover { text-decoration: underline; }

      .seccion {
        padding-top: var(--e7);
        padding-bottom: var(--e8);
        max-width: 620px;
      }
      .tarjeta {
        background: #fff;
        border: 1px solid var(--linea);
        border-radius: 14px;
        padding: var(--e6);
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
      }
      h1 { margin: 0 0 var(--e2); font-size: clamp(24px, 4vw, 30px); }
      .descripcion { margin: 0 0 var(--e5); color: var(--gris); }

      dl { margin: 0; display: flex; flex-direction: column; gap: var(--e3); }
      .fila {
        display: flex;
        justify-content: space-between;
        gap: var(--e4);
        padding-bottom: var(--e3);
        border-bottom: 1px dashed var(--linea);
      }
      dt { color: var(--gris); font-size: 14.5px; }
      dd { margin: 0; font-weight: 600; text-align: right; }

      .nota { margin: var(--e5) 0 0; font-size: 13.5px; color: var(--gris); }
    `,
  ],
})
export class ConfiguracionComponent {
  readonly auth = inject(AuthService);
}
