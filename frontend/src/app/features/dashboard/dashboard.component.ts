import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { Inclinar3dDirective } from '../../shared/directives/inclinar-3d.directive';

@Component({
  selector: 'app-dashboard',
  imports: [Inclinar3dDirective],
  template: `
    <header class="barra">
      <div class="contenedor barra-int">
        <span class="logo">Inter<span class="acento">Soft</span></span>
        <div class="usuario">
          <span>{{ auth.usuario()?.nombre }} · {{ auth.usuario()?.rol }}</span>
          <button class="btn btn-secundario" (click)="salir()">Cerrar sesion</button>
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

  salir(): void {
    this.auth.cerrarSesion();
    this.router.navigate(['/login']);
  }
}
