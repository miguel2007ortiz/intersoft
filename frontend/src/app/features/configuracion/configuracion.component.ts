import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TemaService } from '../../core/services/tema.service';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-configuracion',
  imports: [PanelShellComponent, RouterLink],
  template: `
    <app-panel-shell>
      <section class="contenedor seccion">
        <div class="tarjeta">
          <h1>Configuracion</h1>
          <p class="descripcion">Informacion de tu cuenta y de la empresa.</p>
          <dl>
            <div class="fila">
              <dt>Nombre</dt>
              <dd>{{ auth.usuario()?.nombre }}</dd>
            </div>
            <div class="fila">
              <dt>Correo</dt>
              <dd>{{ auth.usuario()?.email }}</dd>
            </div>
            <div class="fila">
              <dt>Rol</dt>
              <dd>{{ auth.usuario()?.rol }}</dd>
            </div>
            <div class="fila">
              <dt>Empresa</dt>
              <dd>{{ auth.usuario()?.empresa }}</dd>
            </div>
          </dl>

          <h2>Apariencia</h2>
          <div class="fila apariencia">
            <div>
              <dt>Modo noche</dt>
              <p class="ayuda">Cambia entre tema claro y oscuro. Se guarda en este navegador.</p>
            </div>
            <button
              type="button"
              class="interruptor"
              role="switch"
              [attr.aria-checked]="tema.tema() === 'noche'"
              [attr.aria-label]="'Modo noche'"
              [class.activo]="tema.tema() === 'noche'"
              (click)="tema.alternar()"
            >
              <span class="perilla"></span>
            </button>
          </div>
          @if (auth.usuario()?.empresa === null || auth.usuario()?.empresa === undefined) {
            <h2>Empresa</h2>
            <div class="fila empresas">
              <div>
                <dt>¿Tienes un negocio?</dt>
                <p class="ayuda">
                  Registra tu empresa y administra producto, inventario, ventas y mas desde el
                  panel.
                </p>
              </div>
              <a routerLink="/registro" class="btn-negocio">Crear negocio</a>
            </div>
          }

          <p class="nota">Mas opciones de configuracion disponibles proximamente.</p>
        </div>
      </section>
    </app-panel-shell>
  `,
  styles: [
    `
      .seccion {
        padding-top: var(--e7);
        padding-bottom: var(--e8);
        max-width: 620px;
      }
      .tarjeta {
        background: var(--blanco);
        border: 1px solid var(--linea);
        border-radius: 14px;
        padding: var(--e6);
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
      }
      h1 {
        margin: 0 0 var(--e2);
        font-size: clamp(24px, 4vw, 30px);
      }
      .descripcion {
        margin: 0 0 var(--e5);
        color: var(--gris);
      }

      h2 {
        margin: var(--e5) 0 var(--e3);
        font-size: 16px;
        letter-spacing: 0.02em;
      }

      dl {
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: var(--e3);
      }
      .fila {
        display: flex;
        justify-content: space-between;
        gap: var(--e4);
        padding-bottom: var(--e3);
        border-bottom: 1px dashed var(--linea);
      }
      dt {
        color: var(--gris);
        font-size: 14.5px;
      }
      dd {
        margin: 0;
        font-weight: 600;
        text-align: right;
      }

      .apariencia {
        align-items: center;
      }
      .empresas {
        align-items: center;
      }
      .btn-negocio {
        flex: none;
        padding: 9px 18px;
        border-radius: 8px;
        background: var(--primario);
        color: #fff;
        font: inherit;
        font-size: 14px;
        font-weight: 700;
        text-decoration: none;
        transition:
          opacity 0.15s,
          transform 0.1s;
      }
      .btn-negocio:hover {
        opacity: 0.92;
        transform: translateY(-1px);
      }
      .ayuda {
        margin: var(--e1) 0 0;
      }

      .interruptor {
        position: relative;
        flex: none;
        width: 46px;
        height: 26px;
        border-radius: 999px;
        border: none;
        background: var(--linea);
        cursor: pointer;
        transition: background 0.2s ease;
      }
      .interruptor .perilla {
        position: absolute;
        top: 3px;
        left: 3px;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #fff;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease;
      }
      .interruptor.activo {
        background: var(--primario);
      }
      .interruptor.activo .perilla {
        transform: translateX(20px);
      }

      .nota {
        margin: var(--e5) 0 0;
        font-size: 13.5px;
        color: var(--gris);
      }
    `,
  ],
})
export class ConfiguracionComponent {
  readonly auth = inject(AuthService);
  readonly tema = inject(TemaService);
}
