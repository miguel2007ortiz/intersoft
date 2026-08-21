import { Component, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { Inclinar3dDirective } from '../../shared/directives/inclinar-3d.directive';

@Component({
  selector: 'app-dashboard',
  imports: [Inclinar3dDirective, RouterLink],
  template: `
    <header class="barra">
      <div class="contenedor barra-int">
        <span class="logo">Inter<span class="acento">Soft</span></span>
        <div class="usuario">
          <span>{{ auth.usuario()?.nombre }} · {{ auth.usuario()?.rol }}</span>
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
                <a routerLink="/configuracion" (click)="cerrarMenu()">Configuracion</a>
                <button type="button" role="menuitem" class="peligro" (click)="salir()">Cerrar sesion</button>
              </div>
            }
          </div>
        </div>
      </div>
    </header>
    <section class="bienvenida">
      <div class="contenedor">
        <h1>Hola, {{ auth.usuario()?.nombre }}</h1>
        <p>Desde aqui administraras inventario, ventas y reportes de tu negocio.</p>
      </div>
    </section>
    <main class="contenedor modulos">
      @for (m of modulos; track m.titulo) {
        <article class="tarjeta modulo tarjeta-flot" appInclinar3d>
          <h2>{{ m.titulo }}</h2>
          <p>{{ m.texto }}</p>
          <span class="estado insignia-pulso">Proximamente</span>
        </article>
      }
    </main>
  `,
  styles: [
    `
      .barra {
        background: #fff;
        border-bottom: 1px solid var(--linea);
        padding: var(--e3) 0;
      }
      .barra-int {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--e4);
      }
      .logo { font-size: 22px; font-weight: 700; }
      .acento { color: var(--primario); }
      .usuario {
        display: flex;
        align-items: center;
        gap: var(--e4);
        font-size: 14.5px;
        color: var(--gris);
      }

      /* Menu hamburguesa (tres rayitas) con opciones desplegables */
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

      @media (max-width: 640px) {
        .barra-int { flex-direction: column; }
      }
    `,
  ],
})
export class DashboardComponent {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly modulos = [
    { titulo: 'Inventario', texto: 'Control de stock, alertas de minimos y movimientos de producto.' },
    { titulo: 'Ventas y facturacion', texto: 'Registra ventas en el mostrador y genera la factura al instante.' },
    { titulo: 'Reportes', texto: 'Cuanto vendiste, que se mueve y que esta quieto, en un vistazo.' },
  ];

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
