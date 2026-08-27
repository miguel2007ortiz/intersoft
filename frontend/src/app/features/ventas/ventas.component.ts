import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CatalogoService } from '../../core/services/catalogo.service';
import { Venta } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-ventas',
  imports: [DatePipe, DecimalPipe, FormsModule, RouterLink, PanelShellComponent],
  template: `
    <app-panel-shell>
      <div class="ventas">
        <header class="ventas-header">
          <h1>Historial de Ventas</h1>
          <a routerLink="/pos" class="btn-primary">Nueva venta (POS)</a>
        </header>

        <!-- Filtros -->
        <section class="filtros">
          <input type="text" placeholder="Buscar por factura o cliente..."
                 [(ngModel)]="busqueda" (input)="cargarVentas()" class="input" />
          <select [(ngModel)]="filtroEstado" (ngModelChange)="cargarVentas()" class="input input-estado">
            <option value="">Todos los estados</option>
            <option value="completada">Completadas</option>
            <option value="anulada">Anuladas</option>
          </select>
        </section>

        <!-- Estadisticas -->
        @if (estadisticas()) {
          <section class="stats">
            <div class="stat">
              <span class="stat-label">Total ventas</span>
              <span class="stat-valor">{{ estadisticas()!.total_registros }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Monto total</span>
              <span class="stat-valor">{{ estadisticas()!.total_ventas | number }}</span>
            </div>
          </section>
        }

        <!-- Lista -->
        @if (cargando()) {
          <p class="cargando">Cargando ventas...</p>
        } @else if (!ventas().length) {
          <p class="vacio">No hay ventas registradas.</p>
        } @else {
          <div class="tabla-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th>Factura</th>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th>Items</th>
                  <th>Total</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                @for (v of ventas(); track v.id) {
                  <tr>
                    <td class="factura">{{ v.numero_factura }}</td>
                    <td>{{ v.fecha | date:'dd/MM/yy HH:mm' }}</td>
                    <td>{{ v.cliente_nombre }}</td>
                    <td>{{ v.total_items }}</td>
                    <td class="total">{{ v.total | number }}</td>
                    <td>
                      <span class="badge" [class]="v.estado">{{ v.estado }}</span>
                    </td>
                    <td>
                      @if (v.estado === 'completada') {
                        <button type="button" class="btn-anular"
                                (click)="iniciarAnulacion(v)">Anular</button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

        <!-- Modal de anulacion -->
        @if (ventaAnulando()) {
          <div class="modal-overlay" (click)="cancelarAnulacion()">
            <div class="modal" (click)="$event.stopPropagation()">
              <h2>Anular venta</h2>
              <p>Factura: <strong>{{ ventaAnulando()!.numero_factura }}</strong></p>
              <p>Cliente: {{ ventaAnulando()!.cliente_nombre }} — Total: {{ ventaAnulando()!.total | number }}</p>
              <label>Motivo de anulacion</label>
              <textarea [(ngModel)]="motivoAnulacion" class="input" rows="3"
                        placeholder="Describe el motivo..."></textarea>
              @if (errorAnulacion()) {
                <div class="error-box">{{ errorAnulacion() }}</div>
              }
              <div class="modal-acciones">
                <button type="button" class="btn-cancelar" (click)="cancelarAnulacion()">Cancelar</button>
                <button type="button" class="btn-confirmar-anular"
                        [disabled]="!motivoAnulacion || motivoAnulacion.length < 3 || cargandoAnulacion()"
                        (click)="confirmarAnulacion()">
                  @if (cargandoAnulacion()) { Anulando... } @else { Anular venta }
                </button>
              </div>
            </div>
          </div>
        }
      </div>
    </app-panel-shell>
  `,
  styles: [`
    .ventas { max-width: 1000px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .ventas-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--e5); }
    .ventas-header h1 { margin: 0; font-size: clamp(22px, 4vw, 28px); }
    .btn-primary {
      padding: 10px 20px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;
    }

    .filtros { display: flex; gap: var(--e3); margin-bottom: var(--e4); }
    .input {
      padding: 10px 14px; border: 1px solid var(--linea); border-radius: 8px;
      font: inherit; font-size: 14px; background: #fff;
    }
    .input:focus { outline: none; border-color: var(--primario); }
    .input-estado { max-width: 200px; }

    .stats { display: flex; gap: var(--e4); margin-bottom: var(--e5); }
    .stat { background: var(--primario-suave); padding: 12px 20px; border-radius: 8px; }
    .stat-label { display: block; font-size: 12px; color: var(--gris); text-transform: uppercase; letter-spacing: .04em; }
    .stat-valor { font-size: 20px; font-weight: 700; }

    .cargando, .vacio { color: var(--gris); text-align: center; padding: var(--e6); }

    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: 14px; }
    .tabla th { text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--linea); font-weight: 600; }
    .tabla td { padding: 10px 12px; border-bottom: 1px solid var(--linea); }
    .factura { font-family: monospace; font-weight: 600; }
    .total { font-weight: 600; }

    .badge {
      display: inline-block; padding: 3px 10px; border-radius: 999px;
      font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .03em;
    }
    .badge.completada { background: #ecfdf3; color: #067647; }
    .badge.anulada { background: #fef3f2; color: #b42318; }
    .badge.pendiente { background: #fef9ec; color: #b54708; }

    .btn-anular {
      padding: 5px 12px; border: 1px solid #fecdca; background: #fef3f2;
      color: #b42318; border-radius: 6px; cursor: pointer; font: inherit; font-size: 12px;
    }
    .btn-anular:hover { background: #fecdca; }

    .modal-overlay {
      position: fixed; inset: 0; background: rgba(15,23,42,.5);
      display: grid; place-items: center; z-index: 1000;
    }
    .modal {
      background: #fff; border-radius: 14px; padding: var(--e6);
      width: min(480px, 90vw); box-shadow: 0 20px 50px rgba(15,23,42,.2);
    }
    .modal h2 { margin: 0 0 var(--e3); }
    .modal label { display: block; margin-top: var(--e3); margin-bottom: var(--e2); font-weight: 600; font-size: 14px; }
    .modal .input { width: 100%; resize: vertical; }
    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 10px 14px; margin-top: var(--e3); color: #b42318; font-size: 13px;
    }
    .modal-acciones { display: flex; justify-content: flex-end; gap: var(--e3); margin-top: var(--e4); }
    .btn-cancelar {
      padding: 10px 20px; border: 1px solid var(--linea); background: #fff;
      border-radius: 8px; cursor: pointer; font: inherit;
    }
    .btn-confirmar-anular {
      padding: 10px 20px; border: 0; background: #b42318; color: #fff;
      border-radius: 8px; cursor: pointer; font: inherit; font-weight: 600;
    }
    .btn-confirmar-anular:disabled { opacity: .5; cursor: not-allowed; }
  `],
})
export class VentasComponent implements OnInit {
  private readonly catalogo = inject(CatalogoService);

  readonly ventas = signal<Venta[]>([]);
  readonly cargando = signal(true);
  busqueda = '';
  filtroEstado = '';
  readonly estadisticas = signal<{ total_ventas: string; total_registros: number } | null>(null);

  readonly ventaAnulando = signal<Venta | null>(null);
  motivoAnulacion = '';
  readonly cargandoAnulacion = signal(false);
  readonly errorAnulacion = signal('');

  ngOnInit(): void {
    this.cargarVentas();
  }

  cargarVentas(): void {
    this.cargando.set(true);
    this.catalogo.listarVentas({
      estado: this.filtroEstado || undefined,
      busqueda: this.busqueda || undefined,
    }).subscribe({
      next: (r) => {
        this.ventas.set(r.resultados);
        const est = r.estadisticas as { total_ventas: string; total_registros: number } | undefined;
        this.estadisticas.set(est ?? null);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
  }

  iniciarAnulacion(venta: Venta): void {
    this.ventaAnulando.set(venta);
    this.motivoAnulacion = '';
    this.errorAnulacion.set('');
  }

  cancelarAnulacion(): void {
    this.ventaAnulando.set(null);
  }

  confirmarAnulacion(): void {
    const venta = this.ventaAnulando();
    if (!venta || !this.motivoAnulacion) return;

    this.cargandoAnulacion.set(true);
    this.errorAnulacion.set('');

    this.catalogo.anularVenta(venta.id, this.motivoAnulacion).subscribe({
      next: () => {
        this.ventaAnulando.set(null);
        this.cargandoAnulacion.set(false);
        this.cargarVentas();
      },
      error: (e) => {
        this.errorAnulacion.set(e.detalle || 'Error al anular.');
        this.cargandoAnulacion.set(false);
      },
    });
  }
}
