import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoService } from '../../core/services/catalogo.service';
import { InventarioProducto, MovimientoInventario } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-inventario',
  imports: [DatePipe, DecimalPipe, FormsModule, PanelShellComponent],
  template: `
    <app-panel-shell>
      <div class="inventario">
        <header class="inv-header">
          <h1>Inventario</h1>
          <button type="button" class="btn-primary" (click)="mostrarAjuste.set(!mostrarAjuste())">
            @if (mostrarAjuste()) { Ver productos } @else { Ajustar stock }
          </button>
        </header>

        @if (mostrarAjuste()) {
          <!-- Formulario de ajuste manual -->
          <section class="seccion ajuste-form">
            <h2>Ajuste manual de inventario</h2>
            <div class="form-grid">
              <div>
                <label>Producto</label>
                <select [(ngModel)]="ajusteProducto" class="input">
                  <option value="">Seleccionar...</option>
                  @for (p of productos(); track p.id) {
                    <option [value]="p.id">{{ p.nombre }} ({{ p.sku }}) — stock: {{ p.stock }}</option>
                  }
                </select>
              </div>
              <div>
                <label>Tipo</label>
                <select [(ngModel)]="ajusteTipo" class="input">
                  <option value="entrada">Entrada (+)</option>
                  <option value="salida">Salida (-)</option>
                </select>
              </div>
              <div>
                <label>Cantidad</label>
                <input type="number" [(ngModel)]="ajusteCantidad" min="1" class="input" />
              </div>
              <div class="full">
                <label>Motivo</label>
                <input type="text" [(ngModel)]="ajusteMotivo"
                       placeholder="Ej: Conteo fisico, reposicion, merma..."
                       class="input" />
              </div>
            </div>
            @if (errorAjuste()) {
              <div class="error-box">{{ errorAjuste() }}</div>
            }
            @if (exitoAjuste()) {
              <div class="exito-box">{{ exitoAjuste() }}</div>
            }
            <button type="button" class="btn-confirmar" (click)="aplicarAjuste()"
                    [disabled]="!ajusteProducto || !ajusteCantidad || !ajusteMotivo || cargandoAjuste()">
              @if (cargandoAjuste()) { Aplicando... } @else { Aplicar ajuste }
            </button>
          </section>
        } @else {
          <!-- Lista de productos -->
          <section class="filtros">
            <input type="text" placeholder="Buscar producto..."
                   [(ngModel)]="busquedaProducto" (input)="cargarProductos()" class="input" />
            <label class="filtro-stock">
              <input type="checkbox" [(ngModel)]="filtroStockBajo" (ngModelChange)="cargarProductos()" />
              Solo stock bajo
            </label>
          </section>

          @if (cargando()) {
            <p class="cargando">Cargando inventario...</p>
          } @else if (!productos().length) {
            <p class="vacio">No hay productos en inventario.</p>
          } @else {
            <div class="tabla-wrap">
              <table class="tabla">
                <thead>
                  <tr>
                    <th>Producto</th>
                    <th>SKU</th>
                    <th>Categoria</th>
                    <th>Precio</th>
                    <th>Stock</th>
                    <th>Minimo</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  @for (p of productos(); track p.id) {
                    <tr [class.stock-bajo]="p.stock_bajo">
                      <td>{{ p.nombre }}</td>
                      <td class="sku">{{ p.sku }}</td>
                      <td>{{ p.categoria || '—' }}</td>
                      <td>{{ p.precio | number }}</td>
                      <td class="stock">{{ p.stock }}</td>
                      <td>{{ p.stock_minimo }}</td>
                      <td>
                        @if (p.stock_bajo) {
                          <span class="badge alerta">Stock bajo</span>
                        } @else {
                          <span class="badge ok">OK</span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }

          <!-- Historial de movimientos -->
          @if (movimientos().length) {
            <section class="seccion">
              <h2>Ultimos movimientos</h2>
              <div class="tabla-wrap">
                <table class="tabla">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Producto</th>
                      <th>Tipo</th>
                      <th>Cantidad</th>
                      <th>Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (m of movimientos(); track m.id) {
                      <tr>
                        <td>{{ m.created_at | date:'dd/MM/yy HH:mm' }}</td>
                        <td>{{ m.producto_nombre }}</td>
                        <td>
                          <span class="badge-tipo" [class]="m.tipo">{{ m.tipo }}</span>
                        </td>
                        <td>{{ m.tipo === 'salida' ? '-' : '+' }}{{ m.cantidad }}</td>
                        <td>{{ m.motivo }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </section>
          }
        }
      </div>
    </app-panel-shell>
  `,
  styles: [`
    .inventario { max-width: 1000px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .inv-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--e5); }
    .inv-header h1 { margin: 0; font-size: clamp(22px, 4vw, 28px); }
    .btn-primary {
      padding: 10px 20px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-weight: 600; font-size: 14px; cursor: pointer;
    }

    .seccion { margin-bottom: var(--e5); }
    .seccion h2 { margin: 0 0 var(--e3); font-size: 18px; }

    .input {
      width: 100%; padding: 10px 14px; border: 1px solid var(--linea);
      border-radius: 8px; font: inherit; font-size: 14px; background: #fff;
    }
    .input:focus { outline: none; border-color: var(--primario); }

    .filtros { display: flex; gap: var(--e3); align-items: center; margin-bottom: var(--e4); }
    .filtro-stock { font-size: 14px; display: flex; align-items: center; gap: 6px; cursor: pointer; }

    .ajuste-form { background: #fff; border: 1px solid var(--linea); border-radius: 12px; padding: var(--e5); }
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--e3); }
    .full { grid-column: 1 / -1; }
    .form-grid label { display: block; font-weight: 600; font-size: 13px; margin-bottom: 4px; }

    .cargando, .vacio { color: var(--gris); text-align: center; padding: var(--e6); }

    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: 14px; }
    .tabla th { text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--linea); font-weight: 600; }
    .tabla td { padding: 10px 12px; border-bottom: 1px solid var(--linea); }
    .sku { font-family: monospace; }
    .stock { font-weight: 700; }
    .stock-bajo { background: #fef3f2; }

    .badge {
      display: inline-block; padding: 3px 10px; border-radius: 999px;
      font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .03em;
    }
    .badge.ok { background: #ecfdf3; color: #067647; }
    .badge.alerta { background: #fef3f2; color: #b42318; }

    .badge-tipo {
      display: inline-block; padding: 3px 10px; border-radius: 999px;
      font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .badge-tipo.entrada { background: #ecfdf3; color: #067647; }
    .badge-tipo.salida { background: #fef3f2; color: #b42318; }
    .badge-tipo.ajuste { background: #eff8ff; color: #175cd3; }

    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 10px 14px; margin-top: var(--e3); color: #b42318; font-size: 13px;
    }
    .exito-box {
      background: #ecfdf3; border: 1px solid #d1fadf; border-radius: 8px;
      padding: 10px 14px; margin-top: var(--e3); color: #067647; font-size: 13px;
    }

    .btn-confirmar {
      margin-top: var(--e3); padding: 10px 24px; background: var(--primario);
      color: #fff; border: 0; border-radius: 8px; font: inherit; font-weight: 600;
      cursor: pointer;
    }
    .btn-confirmar:disabled { opacity: .5; cursor: not-allowed; }
  `],
})
export class InventarioComponent implements OnInit {
  private readonly catalogo = inject(CatalogoService);

  readonly productos = signal<InventarioProducto[]>([]);
  readonly movimientos = signal<MovimientoInventario[]>([]);
  readonly cargando = signal(true);
  busquedaProducto = '';
  filtroStockBajo = false;
  readonly mostrarAjuste = signal(false);

  ajusteProducto = '';
  ajusteTipo = 'entrada';
  ajusteCantidad = 1;
  ajusteMotivo = '';
  readonly cargandoAjuste = signal(false);
  readonly errorAjuste = signal('');
  readonly exitoAjuste = signal('');

  ngOnInit(): void {
    this.cargarProductos();
    this.cargarMovimientos();
  }

  cargarProductos(): void {
    this.cargando.set(true);
    this.catalogo.listarInventario({
      busqueda: this.busquedaProducto || undefined,
      stock_bajo: this.filtroStockBajo || undefined,
    }).subscribe({
      next: (r) => { this.productos.set(r.resultados); this.cargando.set(false); },
      error: () => this.cargando.set(false),
    });
  }

  cargarMovimientos(): void {
    this.catalogo.listarMovimientos().subscribe({
      next: (r) => this.movimientos.set(r.resultados),
    });
  }

  aplicarAjuste(): void {
    if (!this.ajusteProducto || !this.ajusteCantidad || !this.ajusteMotivo) return;

    this.cargandoAjuste.set(true);
    this.errorAjuste.set('');
    this.exitoAjuste.set('');

    this.catalogo.ajustarInventario({
      producto: this.ajusteProducto,
      cantidad: this.ajusteCantidad,
      tipo: this.ajusteTipo,
      motivo: this.ajusteMotivo,
    }).subscribe({
      next: () => {
        this.exitoAjuste.set('Ajuste aplicado correctamente.');
        this.cargandoAjuste.set(false);
        this.cargarProductos();
        this.cargarMovimientos();
      },
      error: (e) => {
        this.errorAjuste.set(e.detalle || 'Error al aplicar ajuste.');
        this.cargandoAjuste.set(false);
      },
    });
  }
}
