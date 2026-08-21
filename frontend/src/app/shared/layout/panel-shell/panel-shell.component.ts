import { Component, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { BrilloCursorDirective } from '../../directives/brillo-cursor.directive';
import { SiteFooterComponent } from '../site-footer/site-footer.component';

/** Diseno comun de las paginas privadas: resplandor que sigue el cursor,
 * barra superior proyectada, menu hamburguesa con navegacion global
 * (fase 3) y pie armonioso. Usar asi:
 * <app-panel-shell> ...contenido... </app-panel-shell> y dentro del
 * encabezado marcarlo con el atributo panelHeader. */
@Component({
  selector: 'app-panel-shell',
  imports: [BrilloCursorDirective, SiteFooterComponent, RouterLink],
  template: `
    <div class="envoltorio" appBrilloCursor>
      <header class="barra">
        <div class="contenedor barra-int">
          <a routerLink="/dashboard" class="marca" aria-label="Ir al inicio">
            <svg class="icono-inicio" viewBox="0 0 24 24" width="22" height="22"
                 fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 10.5 12 3l9 7.5" />
              <path d="M5 9.5V21h5v-6h4v6h5V9.5" />
            </svg>
            <span>Inter<span class="acento">Soft</span></span>
          </a>
          <ng-content select="[panelHeader]" />
          <div class="usuario">
            <span class="quien">{{ auth.usuario()?.nombre }} · {{ auth.usuario()?.rol }}</span>
            <div class="menu-wrap" (click)="$event.stopPropagation()">
              <button
                type="button"
                class="btn-menu"
                [class.abierto]="menuAbierto()"
                [attr.aria-expanded]="menuAbierto()"
                aria-label="Abrir menu"
                (click)="alternarMenu()"
              >
                <span></span><span></span><span></span>
              </button>
              @if (menuAbierto()) {
                <div class="menu-desplegable" role="menu">
                  @if (auth.usuario()?.rol !== 'CLIENTE') {
                    <a routerLink="/dashboard" (click)="cerrarMenu()">Inicio</a>
                    <a routerLink="/clientes" (click)="cerrarMenu()">Clientes</a>
                    <a routerLink="/productos" (click)="cerrarMenu()">Productos</a>
                  }
                  @if (auth.esAdministrador()) {
                    <a routerLink="/admin/usuarios" (click)="cerrarMenu()">Usuarios</a>
                    <a routerLink="/admin/roles" (click)="cerrarMenu()">Roles y permisos</a>
                  }
                  <a routerLink="/configuracion" (click)="cerrarMenu()">Configuracion</a>
                  <button type="button" role="menuitem" class="peligro" (click)="salir()">
                    Cerrar sesion
                  </button>
                </div>
              }
            </div>
          </div>
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

      /* Marca con icono de inicio: clic lleva al dashboard */
      .marca {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 22px;
        font-weight: 700;
        color: var(--tinta);
        text-decoration: none;
        transition: opacity 0.15s ease;
      }
      .marca:hover { opacity: 0.75; }
      .acento { color: var(--primario); }
      .icono-inicio { color: var(--primario); }

      /* Usuario identificado + menu hamburguesa (tres rayitas) desplegable */
      .usuario {
        display: flex;
        align-items: center;
        gap: var(--e4);
        font-size: 14.5px;
        color: var(--gris);
        margin-left: auto;
      }
      .quien { white-space: nowrap; }

      .menu-wrap { position: relative; }
      .btn-menu {
        display: inline-flex;
        flex-direction: column;
        justify-content: center;
        gap: 5px;
        width: 44px;
        height: 38px;
        padding: 0 10px;
        background: var(--primario-suave);
        border: 1px solid var(--linea);
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.15s ease;
      }
      .btn-menu:hover { background: #e3ebfd; }
      .btn-menu span {
        display: block;
        height: 2px;
        width: 100%;
        border-radius: 2px;
        background: var(--primario-osc);
        transition: transform 0.2s ease, opacity 0.2s ease;
      }
      .btn-menu.abierto span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
      .btn-menu.abierto span:nth-child(2) { opacity: 0; }
      .btn-menu.abierto span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

      .menu-desplegable {
        position: absolute;
        top: calc(100% + 8px);
        right: 0;
        z-index: 600;
        min-width: 190px;
        display: flex;
        flex-direction: column;
        padding: 6px;
        background: #fff;
        border: 1px solid var(--linea);
        border-radius: 10px;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14);
      }
      .menu-desplegable a,
      .menu-desplegable button {
        padding: 10px 12px;
        border: 0;
        border-radius: 7px;
        background: none;
        font: inherit;
        text-align: left;
        color: var(--tinta);
        text-decoration: none;
        cursor: pointer;
      }
      .menu-desplegable a:hover,
      .menu-desplegable button:hover { background: var(--primario-suave); }
      .menu-desplegable button.peligro { color: #b42318; }

      .contenido { flex: 1; }

      @media (max-width: 640px) {
        .barra-int { flex-wrap: wrap; }
        .quien { display: none; }
      }
    `,
  ],
})
export class PanelShellComponent {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly menuAbierto = signal(false);

  alternarMenu(): void {
    this.menuAbierto.update((abierto) => !abierto);
  }

  cerrarMenu(): void {
    this.menuAbierto.set(false);
  }

  /** Cierra el menu al hacer clic fuera de el. */
  @HostListener('document:click')
  cerrarMenuAfuera(): void {
    this.menuAbierto.set(false);
  }

  salir(): void {
    this.auth.cerrarSesion();
    this.router.navigate(['/login']);
  }
}
