import { DecimalPipe } from '@angular/common';
import { Component, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CatalogoService } from '../../core/services/catalogo.service';
import { Cliente, Producto, LineaPOS, VentaPOSInput, StockInsuficiente } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-pos',
  imports: [DecimalPipe, FormsModule, RouterLink, PanelShellComponent],
  template: `
    <app-panel-shell>
      <div class="pos">
        <header class="pos-header">
          <h1>Punto de Venta</h1>
          <a routerLink="/ventas" class="btn-link">Ver historial</a>
        </header>

        <!-- Seleccion de cliente -->
        <section class="seccion">
          <label>Cliente</label>
          <div class="cliente-select">
            <select [(ngModel)]="clienteSeleccionado" class="input">
              <option value="">Seleccionar cliente...</option>
              @for (c of clientes(); track c.id) {
                <option [value]="c.id">{{ c.nombre }} ({{ c.tipo_documento }} {{ c.numero_documento }})</option>
              }
            </select>
            @if (!clientes().length && !cargandoClientes()) {
              <span class="hint">No hay clientes. <a routerLink="/clientes">Crear uno</a></span>
            }
          </div>
        </section>

        <!-- Agregar producto -->
        <section class="seccion">
          <label>Agregar producto</label>
          <div class="producto-add">
            <input type="text" placeholder="Buscar por nombre o SKU..."
                   [(ngModel)]="busquedaProducto" (input)="buscarProductos()"
                   class="input flex-1" />
            @if (resultadosBusqueda().length) {
              <div class="resultados-busqueda">
                @for (p of resultadosBusqueda(); track p.id) {
                  <button type="button" class="resultado-item" (click)="agregarProducto(p)">
                    <span>{{ p.nombre }}</span>
                    <span class="precio">{{ p.precio | number }} — stock: {{ p.stock }}</span>
                  </button>
                }
              </div>
            }
          </div>
        </section>

        <!-- Lineas de venta -->
        @if (lineas().length) {
          <section class="seccion">
            <table class="tabla-lineas">
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Precio</th>
                  <th>Cantidad</th>
                  <th>Subtotal</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                @for (l of lineas(); track l.producto) {
                  <tr>
                    <td>
                      <strong>{{ l.nombre }}</strong>
                      <span class="sku">{{ l.sku }}</span>
                    </td>
                    <td>{{ l.precio_unitario | number }}</td>
                    <td>
                      <input type="number" [(ngModel)]="l.cantidad" min="1"
                             [max]="l.stock_disponible" (ngModelChange)="recalcular()"
                             class="input-cantidad" />
                      <span class="stock-info">/{{ l.stock_disponible }}</span>
                    </td>
                    <td>{{ l.subtotal | number }}</td>
                    <td>
                      <button type="button" class="btn-eliminar" (click)="eliminarLinea(l)">✕</button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </section>
        }

        <!-- Descuento y notas -->
        <section class="seccion resumen">
          <div class="descuento-notas">
            <div>
              <label>Descuento ($)</label>
              <input type="number" [(ngModel)]="descuento" min="0"
                     (ngModelChange)="recalcular()" class="input input-descuento" />
            </div>
            <div class="flex-1">
              <label>Notas</label>
              <textarea [(ngModel)]="notas" placeholder="Opcional..." class="input" rows="2"></textarea>
            </div>
          </div>
        </section>

        <!-- Totales -->
        <section class="seccion totales">
          <div class="totales-fila"><span>Subtotal</span><span>{{ subtotal() | number }}</span></div>
          @if (descuento > 0) {
            <div class="totales-fila descuento"><span>Descuento</span><span>-{{ descuento | number }}</span></div>
          }
          <div class="totales-fila total"><span>Total</span><span>{{ total() | number }}</span></div>
        </section>

        <!-- Metodo de pago -->
        <section class="seccion">
          <label>Metodo de pago</label>
          <div class="metodos-pago">
            @for (m of metodosPago; track m.valor) {
              <button type="button"
                      [class.activo]="metodoPago() === m.valor"
                      (click)="metodoPago.set(m.valor)"
                      class="btn-metodo">
                {{ m.etiqueta }}
              </button>
            }
          </div>
        </section>

        <!-- Errores -->
        @if (error()) {
          <div class="error-box">{{ error() }}</div>
        }
        @if (erroresStock().length) {
          <div class="error-box">
            <strong>Stock insuficiente:</strong>
            @for (e of erroresStock(); track e.producto) {
              <div>{{ e.producto_nombre }}: solicita {{ e.solicitado }}, disponible {{ e.disponible }}</div>
            }
          </div>
        }

        <!-- Boton confirmar -->
        <section class="seccion acciones">
          <button type="button" class="btn-confirmar"
                  [disabled]="!puedeConfirmar() || cargando()"
                  (click)="confirmarVenta()">
            @if (cargando()) { Procesando... } @else { Confirmar venta }
          </button>
        </section>

        <!-- Exito -->
        @if (ventaCreada()) {
          <div class="exito-box">
            <strong>Venta registrada!</strong>
            Factura: {{ ventaCreada()!.numero_factura }} — Total: {{ ventaCreada()!.total | number }}
            <button type="button" class="btn-nueva" (click)="nuevaVenta()">Nueva venta</button>
          </div>
        }
      </div>
    </app-panel-shell>
  `,
  styles: [`
    .pos { max-width: 900px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .pos-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--e5); }
    .pos-header h1 { margin: 0; font-size: clamp(22px, 4vw, 28px); }
    .btn-link { color: var(--primario); text-decoration: none; font-weight: 600; font-size: 14px; }
    .btn-link:hover { text-decoration: underline; }

    .seccion { margin-bottom: var(--e5); }
    .seccion label { display: block; font-weight: 600; margin-bottom: var(--e2); font-size: 14px; }

    .input {
      width: 100%; padding: 10px 14px; border: 1px solid var(--linea);
      border-radius: 8px; font: inherit; font-size: 14px;
      background: #fff; transition: border-color .15s;
    }
    .input:focus { outline: none; border-color: var(--primario); }
    .flex-1 { flex: 1; }

    .cliente-select { position: relative; }
    .hint { display: block; margin-top: var(--e1); font-size: 13px; color: var(--gris); }
    .hint a { color: var(--primario); }

    .producto-add { position: relative; display: flex; gap: var(--e3); }
    .resultados-busqueda {
      position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
      background: #fff; border: 1px solid var(--linea); border-radius: 8px;
      box-shadow: 0 8px 24px rgba(15,23,42,.12); max-height: 240px; overflow-y: auto;
    }
    .resultado-item {
      display: flex; justify-content: space-between; width: 100%; padding: 10px 14px;
      border: 0; background: none; text-align: left; cursor: pointer; font: inherit;
    }
    .resultado-item:hover { background: var(--primario-suave); }
    .resultado-item .precio { font-size: 13px; color: var(--gris); }

    .tabla-lineas { width: 100%; border-collapse: collapse; font-size: 14px; }
    .tabla-lineas th { text-align: left; padding: 8px; border-bottom: 2px solid var(--linea); font-weight: 600; }
    .tabla-lineas td { padding: 8px; border-bottom: 1px solid var(--linea); }
    .sku { display: block; font-size: 12px; color: var(--gris); }
    .input-cantidad { width: 60px; padding: 6px 8px; border: 1px solid var(--linea); border-radius: 6px; text-align: center; font: inherit; }
    .input-cantidad:focus { outline: none; border-color: var(--primario); }
    .stock-info { font-size: 12px; color: var(--gris); margin-left: 4px; }
    .btn-eliminar { border: 0; background: none; color: #b42318; cursor: pointer; font-size: 16px; padding: 4px 8px; }

    .descuento-notas { display: flex; gap: var(--e4); }
    .input-descuento { max-width: 160px; }

    .totales { text-align: right; }
    .totales-fila { display: flex; justify-content: space-between; padding: 6px 0; font-size: 15px; }
    .totales-fila.descuento { color: #b42318; }
    .totales-fila.total { font-size: 20px; font-weight: 700; border-top: 2px solid var(--linea); padding-top: 10px; margin-top: 4px; }

    .metodos-pago { display: flex; gap: var(--e2); flex-wrap: wrap; }
    .btn-metodo {
      padding: 8px 16px; border: 1px solid var(--linea); border-radius: 8px;
      background: #fff; cursor: pointer; font: inherit; font-size: 13px;
      transition: all .15s;
    }
    .btn-metodo:hover { border-color: var(--primario); }
    .btn-metodo.activo { background: var(--primario); color: #fff; border-color: var(--primario); }

    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 12px 16px; margin-bottom: var(--e4); color: #b42318; font-size: 14px;
    }
    .error-box strong { display: block; margin-bottom: 4px; }

    .acciones { text-align: right; }
    .btn-confirmar {
      padding: 12px 32px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-size: 15px;
      font-weight: 600; cursor: pointer; transition: opacity .15s;
    }
    .btn-confirmar:hover { opacity: .9; }
    .btn-confirmar:disabled { opacity: .5; cursor: not-allowed; }

    .exito-box {
      background: #ecfdf3; border: 1px solid #d1fadf; border-radius: 8px;
      padding: 16px; margin-top: var(--e4); color: #067647; font-size: 14px;
    }
    .exito-box strong { display: block; margin-bottom: 4px; font-size: 16px; }
    .btn-nueva {
      margin-top: 8px; padding: 8px 20px; background: var(--primario);
      color: #fff; border: 0; border-radius: 6px; cursor: pointer; font: inherit;
    }
  `],
})
export class PosComponent {
  private readonly catalogo = inject(CatalogoService);

  readonly clientes = signal<Cliente[]>([]);
  readonly cargandoClientes = signal(true);
  busquedaProducto = '';
  readonly resultadosBusqueda = signal<Producto[]>([]);
  readonly lineas = signal<LineaPOS[]>([]);
  descuento = 0;
  notas = '';
  readonly metodoPago = signal('efectivo');
  readonly cargando = signal(false);
  readonly error = signal('');
  readonly erroresStock = signal<StockInsuficiente[]>([]);
  readonly ventaCreada = signal<any>(null);

  readonly metodosPago = [
    { valor: 'efectivo', etiqueta: 'Efectivo' },
    { valor: 'transferencia', etiqueta: 'Transferencia' },
    { valor: 'nequi', etiqueta: 'Nequi' },
    { valor: 'daviplata', etiqueta: 'Daviplata' },
    { valor: 'tarjeta', etiqueta: 'Tarjeta' },
  ];

  readonly subtotal = computed(() =>
    this.lineas().reduce((sum, l) => sum + l.subtotal, 0));
  readonly total = computed(() =>
    Math.max(this.subtotal() - this.descuento, 0));
  readonly puedeConfirmar = computed(() =>
    this.lineas().length > 0 && !!this.clienteSeleccionado);

  clienteSeleccionado = '';

  constructor() {
    this.cargarClientes();
  }

  cargarClientes(): void {
    this.catalogo.listarClientes().subscribe({
      next: (r) => { this.clientes.set(r.resultados); this.cargandoClientes.set(false); },
      error: () => this.cargandoClientes.set(false),
    });
  }

  buscarProductos(): void {
    if (this.busquedaProducto.length < 2) {
      this.resultadosBusqueda.set([]);
      return;
    }
    this.catalogo.listarProductos({ busqueda: this.busquedaProducto, activo: true })
      .subscribe({
        next: (r) => this.resultadosBusqueda.set(r.resultados),
        error: () => this.resultadosBusqueda.set([]),
      });
  }

  agregarProducto(producto: Producto): void {
    const existente = this.lineas().find(l => l.producto === producto.id);
    if (existente) {
      existente.cantidad += 1;
      existente.subtotal = existente.cantidad * existente.precio_unitario;
      this.lineas.update(l => [...l]);
    } else {
      this.lineas.update(l => [...l, {
        producto: producto.id,
        nombre: producto.nombre,
        sku: producto.sku,
        precio_unitario: Number(producto.precio),
        cantidad: 1,
        stock_disponible: producto.stock,
        subtotal: Number(producto.precio),
      }]);
    }
    this.resultadosBusqueda.set([]);
    this.busquedaProducto = '';
  }

  eliminarLinea(linea: LineaPOS): void {
    this.lineas.update(l => l.filter(x => x.producto !== linea.producto));
  }

  recalcular(): void {
    this.lineas.update(l => l.map(linea => ({
      ...linea,
      cantidad: Math.max(1, Math.min(linea.cantidad, linea.stock_disponible)),
      subtotal: Math.max(1, Math.min(linea.cantidad, linea.stock_disponible)) * linea.precio_unitario,
    })));
  }

  confirmarVenta(): void {
    if (!this.clienteSeleccionado || !this.lineas().length) return;

    this.cargando.set(true);
    this.error.set('');
    this.erroresStock.set([]);

    const input: VentaPOSInput = {
      cliente: this.clienteSeleccionado,
      metodo_pago: this.metodoPago(),
      descuento: this.descuento,
      notas: this.notas,
      detalles: this.lineas().map(l => ({
        producto: l.producto,
        cantidad: l.cantidad,
      })),
    };

    this.catalogo.crearVentaPOS(input).subscribe({
      next: (venta) => {
        this.ventaCreada.set(venta);
        this.cargando.set(false);
      },
      error: (e) => {
        if (e.codigo === 'STOCK_INSUFICIENTE') {
          this.erroresStock.set(e.productos || []);
        } else {
          this.error.set(e.detalle || 'Error al crear la venta.');
        }
        this.cargando.set(false);
      },
    });
  }

  nuevaVenta(): void {
    this.lineas.set([]);
    this.descuento = 0;
    this.notas = '';
    this.clienteSeleccionado = '';
    this.ventaCreada.set(null);
    this.error.set('');
    this.erroresStock.set([]);
  }
}
