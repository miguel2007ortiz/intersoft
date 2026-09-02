import { DecimalPipe, DatePipe } from '@angular/common';
import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { Pedido } from '../../../core/models/tienda.model';

@Component({
  selector: 'app-pedidos',
  imports: [DecimalPipe, DatePipe, RouterLink],
  template: `
    <div class="pedidos">
      <header class="pedidos-header">
        <a routerLink="/catalogo" class="btn-volver">&larr; Seguir comprando</a>
        <h1>Mis pedidos</h1>
      </header>

      @if (cargando()) {
        <div class="cargando">Cargando tus pedidos...</div>
      } @else if (error()) {
        <div class="error-box" role="alert">
          <p>{{ error() }}</p>
          <button type="button" class="btn-reintentar" (click)="cargarPedidos()">Reintentar</button>
        </div>
      } @else if (!pedidos().length) {
        <div class="vacio">
          <p>Todavia no has hecho ningun pedido.</p>
          <a routerLink="/catalogo" class="btn-seguir">Ver productos</a>
        </div>
      } @else {
        <section class="lista">
          @for (p of pedidos(); track p.id; let i = $index) {
            <article class="pedido aparecer" [style.--retraso.ms]="(i % 10) * 60">
              <header class="pedido-cabecera">
                <div>
                  <strong>{{ p.numero_factura }}</strong>
                  <span class="pedido-empresa">{{ p.empresa_nombre }}</span>
                </div>
                <div class="pedido-meta">
                  <span class="pedido-fecha">{{ p.created_at | date: 'd MMM y, h:mm a' }}</span>
                  <span class="estado" [class]="'estado-' + p.estado">{{ p.estado }}</span>
                </div>
              </header>

              <ul class="lineas">
                @for (d of p.detalles; track d.id) {
                  <li>
                    <span>{{ d.cantidad }} x {{ d.producto_nombre }}</span>
                    <span>\${{ d.subtotal_linea | number }}</span>
                  </li>
                }
              </ul>

              <footer class="pedido-pie">
                @if (Number(p.descuento) > 0) {
                  <span class="pedido-descuento">Descuento: -\${{ p.descuento | number }}</span>
                }
                <span class="pedido-total">Total: \${{ p.total | number }}</span>
              </footer>
            </article>
          }
        </section>
      }
    </div>
  `,
  styles: [`
    .pedidos { max-width: 800px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .pedidos-header { margin-bottom: var(--e5); }
    .pedidos-header h1 { margin: 8px 0 0; font-size: clamp(22px, 4vw, 28px); }
    .btn-volver { color: var(--primario); text-decoration: none; font-weight: 600; font-size: 14px; }
    .btn-volver:hover { text-decoration: underline; }

    .cargando, .vacio { text-align: center; padding: var(--e6); color: var(--gris); }
    .vacio p { font-size: 16px; margin-bottom: var(--e3); }
    .btn-seguir {
      display: inline-block; padding: 10px 24px; background: var(--primario); color: #fff;
      border-radius: 8px; text-decoration: none; font-weight: 600;
    }
    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 12px 16px; color: #b42318; font-size: 14px;
      display: flex; align-items: center; justify-content: space-between; gap: var(--e3);
    }
    .error-box p { margin: 0; }
    .btn-reintentar {
      padding: 8px 18px; border: 1px solid #fecdca; background: #fff;
      border-radius: 8px; cursor: pointer; font: inherit; font-size: 13px; font-weight: 600;
      white-space: nowrap;
    }
    .btn-reintentar:hover { border-color: #b42318; color: #b42318; }

    .lista { display: flex; flex-direction: column; gap: var(--e4); }
    .pedido {
      border: 1px solid var(--linea); border-radius: 12px; padding: var(--e4);
      background: #fff; transition: box-shadow .2s;
    }
    .pedido:hover { box-shadow: 0 8px 24px rgba(15,23,42,.08); }
    .pedido-cabecera {
      display: flex; justify-content: space-between; align-items: flex-start;
      flex-wrap: wrap; gap: var(--e2); margin-bottom: var(--e3);
      padding-bottom: var(--e3); border-bottom: 1px solid var(--linea);
    }
    .pedido-empresa { display: block; font-size: 12.5px; color: var(--gris); margin-top: 2px; }
    .pedido-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
    .pedido-fecha { font-size: 12.5px; color: var(--gris); }
    .estado {
      font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 3px 10px;
      border-radius: 999px; letter-spacing: .02em;
    }
    .estado-completada { background: #ecfdf3; color: #067647; }
    .estado-pendiente { background: #fffaeb; color: #b54708; }
    .estado-anulada { background: #fef3f2; color: #b42318; }

    .lineas { list-style: none; margin: 0 0 var(--e3); padding: 0; display: flex; flex-direction: column; gap: 6px; }
    .lineas li { display: flex; justify-content: space-between; font-size: 14px; color: var(--tinta); }

    .pedido-pie { display: flex; justify-content: flex-end; gap: var(--e4); font-size: 14px; }
    .pedido-descuento { color: #b42318; }
    .pedido-total { font-weight: 700; }
  `],
})
export class PedidosComponent implements OnInit {
  private readonly tienda = inject(TiendaService);

  readonly pedidos = signal<Pedido[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');

  Number = Number;

  ngOnInit(): void {
    this.cargarPedidos();
  }

  cargarPedidos(): void {
    this.cargando.set(true);
    this.tienda.misPedidos().subscribe({
      next: (r) => {
        this.pedidos.set(r.resultados);
        this.error.set('');
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al cargar tus pedidos.');
        this.cargando.set(false);
      },
    });
  }
}
