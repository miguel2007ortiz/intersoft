import { DatePipe, DecimalPipe, SlicePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoService } from '../../core/services/catalogo.service';
import { FacturaElectronica, NotaCredito, Venta } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { programarAviso } from '../../core/utils/temporizador.util';

@Component({
  selector: 'app-facturacion',
  imports: [DecimalPipe, SlicePipe, DatePipe, FormsModule, PanelShellComponent],
  template: `
    <app-panel-shell>
      <div class="facturacion">
        <header class="page-header">
          <h1>Facturacion DIAN</h1>
        </header>

        <!-- Tabs -->
        <nav class="tabs">
          <button [class.activo]="pestana() === 'facturas'" (click)="pestana.set('facturas')">
            Facturas Electronicas
          </button>
          <button [class.activo]="pestana() === 'notas'" (click)="pestana.set('notas'); cargarNotasCredito()">
            Notas Credito
          </button>
          <button [class.activo]="pestana() === 'generar'" (click)="pestana.set('generar'); cargarVentas()">
            Generar Factura
          </button>
        </nav>

        <!-- ===== TAB: Facturas ===== -->
        @if (pestana() === 'facturas') {
          <section class="filtros">
            <input type="text" aria-label="Buscar factura" placeholder="Buscar por numero, CUFE, cliente..."
                   [(ngModel)]="busquedaFactura" (input)="cargarFacturas()" class="input" />
            <select [(ngModel)]="filtroEstado" (change)="cargarFacturas()" class="input input-select">
              <option value="">Todos los estados</option>
              <option value="pendiente">Pendiente</option>
              <option value="enviada">Enviada</option>
              <option value="aprobada">Aprobada</option>
              <option value="rechazada">Rechazada</option>
              <option value="fallida">Fallida</option>
            </select>
          </section>

          @if (cargando()) {
            <div class="cargando">Cargando facturas...</div>
          } @else if (error()) {
            <div class="error-box">{{ error() }}</div>
          } @else if (!facturas().length) {
            <div class="vacio">No hay facturas electronicas.</div>
          } @else {
            <table class="tabla">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Venta</th>
                  <th>Cliente</th>
                  <th>Total</th>
                  <th>Estado</th>
                  <th>CUFE</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                @for (f of facturas(); track f.id) {
                  <tr>
                    <td class="monospace">{{ f.numero }}</td>
                    <td>{{ f.venta_numero }}</td>
                    <td>{{ f.cliente_nombre }}</td>
                    <td>{{ f.venta_total | number }} COP</td>
                    <td>
                      <span class="badge" [attr.data-estado]="f.estado">
                        {{ f.estado_display }}
                      </span>
                    </td>
                    <td class="monospace cufe">{{ f.cufe ? (f.cufe | slice:0:20) + '...' : '—' }}</td>
                    <td class="acciones-celda">
                      @if (f.estado === 'aprobada') {
                        <button class="btn-sm btn-primary" (click)="reenviar(f)">Reenviar</button>
                      }
                      @if (f.estado === 'fallida' || f.estado === 'rechazada') {
                        <button class="btn-sm btn-warning" (click)="reintentar(f)"
                                [disabled]="accionId() === f.id">
                          @if (accionId() === f.id) { Reintentando... } @else { Reintentar }
                        </button>
                      }
                      @if (f.estado === 'rechazada' && f.motivo_rechazo) {
                        <button class="btn-sm btn-outline" (click)="verDetalle(f)">
                          Ver motivo
                        </button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          }
        }

        <!-- ===== TAB: Generar Factura ===== -->
        @if (pestana() === 'generar') {
          <section class="seccion">
            <p class="hint">Selecciona una venta completada sin factura electronica para generarla.</p>
            @if (cargandoVentas()) {
              <div class="cargando">Cargando ventas...</div>
            } @else if (!ventasDisponibles().length) {
              <div class="vacio">No hay ventas pendientes de facturar.</div>
            } @else {
              <table class="tabla">
                <thead>
                  <tr>
                    <th>Factura</th>
                    <th>Cliente</th>
                    <th>Total</th>
                    <th>Fecha</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  @for (v of ventasDisponibles(); track v.id) {
                    <tr>
                      <td>{{ v.numero_factura }}</td>
                      <td>{{ v.cliente_nombre }}</td>
                      <td>{{ v.total | number }} COP</td>
                      <td>{{ v.fecha | date:'dd/MM/yyyy HH:mm' }}</td>
                      <td>
                        <button class="btn-sm btn-primary"
                                [disabled]="generandoId() === v.id"
                                (click)="generarFactura(v)">
                          @if (generandoId() === v.id) { Generando... } @else { Generar FE }
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            }
          </section>
        }

        <!-- ===== TAB: Notas Credito ===== -->
        @if (pestana() === 'notas') {
          <section class="seccion">
            <div class="section-header">
              <p class="hint">Notas credito para reversar ventas ya facturadas ante la DIAN.</p>
              <button class="btn-sm btn-primary" (click)="pestana.set('crear-nc'); cargarVentasFacturadas()">
                + Nota Credito
              </button>
            </div>

            @if (cargandoNotas()) {
              <div class="cargando">Cargando notas credito...</div>
            } @else if (!notasCredito().length) {
              <div class="vacio">No hay notas credito.</div>
            } @else {
              <table class="tabla">
                <thead>
                  <tr>
                    <th>Numero</th>
                    <th>Venta original</th>
                    <th>Cliente</th>
                    <th>Total</th>
                    <th>Estado</th>
                    <th>Reverso stock</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  @for (nc of notasCredito(); track nc.id) {
                    <tr>
                      <td class="monospace">{{ nc.numero }}</td>
                      <td>{{ nc.venta_numero }}</td>
                      <td>{{ nc.cliente_nombre }}</td>
                      <td>{{ nc.venta_total | number }} COP</td>
                      <td>
                        <span class="badge" [attr.data-estado]="nc.estado === 'aprobada' ? 'aprobada' : nc.estado === 'rechazada' ? 'rechazada' : 'pendiente'">
                          {{ nc.estado_display }}
                        </span>
                      </td>
                      <td>{{ nc.reverso_stock ? '✓' : '—' }}</td>
                      <td>{{ nc.motivo }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            }
          </section>
        }

        <!-- ===== Crear Nota Credito ===== -->
        @if (pestana() === 'crear-nc') {
          <section class="seccion">
            <h2>Crear Nota Credito</h2>
            <p class="hint">Selecciona una venta facturada y proporciona el motivo del reverso.</p>
            @if (!ventasFacturadas().length) {
              <div class="vacio">No hay ventas facturadas disponibles para nota credito.</div>
            } @else {
              <div class="nc-form">
                <select [(ngModel)]="ventaNcSeleccionada" class="input">
                  <option value="">Seleccionar venta...</option>
                  @for (v of ventasFacturadas(); track v.id) {
                    <option [value]="v.id">{{ v.numero_factura }} — {{ v.cliente_nombre }} — {{ v.total | number }} COP</option>
                  }
                </select>
                <textarea [(ngModel)]="motivoNc" placeholder="Motivo de la nota credito..."
                          class="input" rows="3"></textarea>
                <button class="btn-primary" [disabled]="!ventaNcSeleccionada || !motivoNc || creandoNc()"
                        (click)="crearNotaCredito()">
                  @if (creandoNc()) { Procesando... } @else { Crear Nota Credito }
                </button>
              </div>
            }
          </section>
        }

        <!-- Modal detalle / motivo rechazo -->
        @if (detalleVisible()) {
          <div class="modal-overlay" (click)="detalleVisible.set(false)">
            <div class="modal" (click)="$event.stopPropagation()">
              <h3>Detalle de Factura</h3>
              @if (detalleSeleccion()) {
                <div class="modal-body">
                  <p><strong>Numero:</strong> {{ detalleSeleccion()!.numero }}</p>
                  <p><strong>Estado:</strong> {{ detalleSeleccion()!.estado_display }}</p>
                  <p><strong>CUFE:</strong></p>
                  <pre class="cufe-full">{{ detalleSeleccion()!.cufe || 'Sin CUFE' }}</pre>
                  @if (detalleSeleccion()!.motivo_rechazo) {
                    <div class="motivo-rechazo">
                      <strong>Motivo de rechazo:</strong>
                      <p>{{ detalleSeleccion()!.motivo_rechazo }}</p>
                    </div>
                  }
                  <p><strong>Intentos:</strong> {{ detalleSeleccion()!.intentos }}</p>
                  <p><strong>Correo enviado:</strong> {{ detalleSeleccion()!.enviado_correo ? 'Si' : 'No' }}</p>
                </div>
              }
              <button class="btn-outline" (click)="detalleVisible.set(false)">Cerrar</button>
            </div>
          </div>
        }

        <!-- Modal reenviar -->
        @if (reenviarVisible()) {
          <div class="modal-overlay" (click)="reenviarVisible.set(false)">
            <div class="modal" (click)="$event.stopPropagation()">
              <h3>Reenviar Factura</h3>
              <p>Factura: <strong>{{ facturaReenviar()?.numero }}</strong></p>
              <p>Cliente: {{ facturaReenviar()?.cliente_nombre }}</p>
              <div class="nc-form">
                <input type="email" [(ngModel)]="emailReenvio" placeholder="Email destino (opcional)"
                       class="input" />
                <button class="btn-primary" [disabled]="reenviando()"
                        (click)="confirmarReenvio()">
                  @if (reenviando()) { Enviando... } @else { Enviar }
                </button>
                <button class="btn-outline" (click)="reenviarVisible.set(false)">Cancelar</button>
              </div>
              @if (exitoReenvio()) {
                <div class="exito-inline">{{ exitoReenvio() }}</div>
              }
            </div>
          </div>
        }

        <!-- Toast exito -->
        @if (exito()) {
          <div class="exito-toast">{{ exito() }}</div>
        }
      </div>
    </app-panel-shell>
  `,
  styles: [`
    .facturacion { max-width: 1100px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .page-header { margin-bottom: var(--e4); }
    .page-header h1 { margin: 0; font-size: clamp(22px, 4vw, 28px); }

    .tabs {
      display: flex; gap: 0; border-bottom: 2px solid var(--linea);
      margin-bottom: var(--e5);
    }
    .tabs button {
      padding: 10px 20px; border: 0; background: none; cursor: pointer;
      font: inherit; font-size: 14px; color: var(--gris);
      border-bottom: 2px solid transparent; margin-bottom: -2px;
      transition: all .15s;
    }
    .tabs button:hover { color: var(--texto); }
    .tabs button.activo {
      color: var(--primario); font-weight: 600;
      border-bottom-color: var(--primario);
    }

    .filtros { display: flex; gap: var(--e3); flex-wrap: wrap; margin-bottom: var(--e4); }
    .input {
      padding: 10px 14px; border: 1px solid var(--linea);
      border-radius: 8px; font: inherit; font-size: 14px;
      background: #fff; transition: border-color .15s;
    }
    .input:focus { outline: none; border-color: var(--primario); }
    .input-select { min-width: 180px; }

    .cargando, .vacio { text-align: center; padding: var(--e6); color: var(--gris); font-size: 15px; }
    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 12px 16px; color: #b42318; font-size: 14px;
    }

    .tabla { width: 100%; border-collapse: collapse; font-size: 14px; }
    .tabla th {
      text-align: left; padding: 10px 8px;
      border-bottom: 2px solid var(--linea); font-weight: 600; font-size: 13px;
    }
    .tabla td { padding: 10px 8px; border-bottom: 1px solid var(--linea); }
    .monospace { font-family: monospace; font-size: 13px; }
    .cufe { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .acciones-celda { display: flex; gap: 6px; flex-wrap: wrap; }

    .badge {
      display: inline-block; padding: 3px 10px; border-radius: 12px;
      font-size: 12px; font-weight: 600; text-transform: uppercase;
    }
    .badge[data-estado="aprobada"] { background: #ecfdf3; color: #067647; }
    .badge[data-estado="rechazada"] { background: #fef3f2; color: #b42318; }
    .badge[data-estado="fallida"] { background: #fef3f2; color: #b42318; }
    .badge[data-estado="pendiente"] { background: #fff8ed; color: #b54708; }
    .badge[data-estado="enviada"] { background: #eff8ff; color: #175cd3; }

    .btn-sm {
      padding: 4px 10px; border: 1px solid var(--linea); border-radius: 6px;
      background: #fff; cursor: pointer; font: inherit; font-size: 12px;
      font-weight: 600; transition: all .15s;
    }
    .btn-sm:hover { border-color: var(--primario); }
    .btn-sm:disabled { opacity: .5; cursor: not-allowed; }
    .btn-primary { background: var(--primario); color: #fff; border-color: var(--primario); }
    .btn-primary:hover { opacity: .9; }
    .btn-warning { background: #b54708; color: #fff; border-color: #b54708; }
    .btn-outline { background: #fff; }

    .hint { font-size: 14px; color: var(--gris); margin-bottom: var(--e3); }
    .section-header { display: flex; justify-content: space-between; align-items: center; }
    .section-header .hint { margin-bottom: 0; }

    .nc-form { display: flex; flex-direction: column; gap: var(--e3); max-width: 500px; }
    .nc-form .btn-primary { align-self: flex-start; padding: 10px 24px; }

    .modal-overlay {
      position: fixed; inset: 0; z-index: 9000;
      background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center;
    }
    .modal {
      background: #fff; border-radius: 12px; padding: 24px;
      max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto;
    }
    .modal h3 { margin: 0 0 var(--e3); }
    .modal-body p { margin: 6px 0; font-size: 14px; }
    .cufe-full {
      background: #f1f5f9; padding: 10px; border-radius: 6px;
      font-size: 12px; word-break: break-all; margin: 4px 0;
    }
    .motivo-rechazo {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 6px;
      padding: 10px; margin: 8px 0; color: #b42318; font-size: 13px;
    }
    .exito-inline {
      background: #ecfdf3; border: 1px solid #d1fadf; border-radius: 6px;
      padding: 10px; margin-top: var(--e2); color: #067647; font-size: 13px;
    }

    .exito-toast {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      background: #067647; color: #fff; padding: 12px 24px;
      border-radius: 8px; font-size: 14px; font-weight: 600;
      box-shadow: 0 8px 24px rgba(6,118,71,.3);
    }
  `],
})
export class FacturacionComponent implements OnInit {
  private readonly catalogo = inject(CatalogoService);
  private readonly destroyRef = inject(DestroyRef);

  readonly pestana = signal<'facturas' | 'notas' | 'generar' | 'crear-nc'>('facturas');
  readonly facturas = signal<FacturaElectronica[]>([]);
  readonly notasCredito = signal<NotaCredito[]>([]);
  readonly ventasDisponibles = signal<Venta[]>([]);
  readonly ventasFacturadas = signal<Venta[]>([]);
  readonly cargando = signal(true);
  readonly cargandoVentas = signal(false);
  readonly cargandoNotas = signal(false);
  readonly error = signal('');
  readonly exito = signal('');
  readonly accionId = signal<string | null>(null);
  readonly generandoId = signal<string | null>(null);

  readonly detalleVisible = signal(false);
  readonly detalleSeleccion = signal<FacturaElectronica | null>(null);
  readonly reenviarVisible = signal(false);
  readonly facturaReenviar = signal<FacturaElectronica | null>(null);
  readonly reenviando = signal(false);
  readonly exitoReenvio = signal('');

  readonly creandoNc = signal(false);

  busquedaFactura = '';
  filtroEstado = '';
  ventaNcSeleccionada = '';
  motivoNc = '';
  emailReenvio = '';

  ngOnInit(): void {
    this.cargarFacturas();
  }

  cargarFacturas(): void {
    this.cargando.set(true);
    this.error.set('');
    this.catalogo.listarFacturas({
      busqueda: this.busquedaFactura,
      estado: this.filtroEstado,
    }).subscribe({
      next: (r) => { this.facturas.set(r.resultados); this.cargando.set(false); },
      error: (e) => { this.error.set(e.detalle || 'Error al cargar.'); this.cargando.set(false); },
    });
  }

  cargarVentas(): void {
    this.cargandoVentas.set(true);
    this.catalogo.listarVentas({ estado: 'completada' }).subscribe({
      next: (r) => {
        this.ventasDisponibles.set(r.resultados);
        this.cargandoVentas.set(false);
      },
      error: () => this.cargandoVentas.set(false),
    });
  }

  cargarVentasFacturadas(): void {
    this.cargandoVentas.set(true);
    this.catalogo.listarFacturas({ estado: 'aprobada' }).subscribe({
      next: (r) => {
        const ids = r.resultados.map(f => f.venta);
        this.catalogo.listarVentas({ estado: 'completada' }).subscribe({
          next: (vr) => {
            this.ventasFacturadas.set(vr.resultados.filter(v => ids.includes(v.id)));
            this.cargandoVentas.set(false);
          },
          error: () => this.cargandoVentas.set(false),
        });
      },
      error: () => this.cargandoVentas.set(false),
    });
  }

  cargarNotasCredito(): void {
    this.cargandoNotas.set(true);
    this.catalogo.listarNotasCredito().subscribe({
      next: (r) => { this.notasCredito.set(r.resultados); this.cargandoNotas.set(false); },
      error: () => this.cargandoNotas.set(false),
    });
  }

  generarFactura(venta: Venta): void {
    this.generandoId.set(venta.id);
    this.error.set('');
    this.catalogo.generarFactura(venta.id).subscribe({
      next: (f) => {
        this.generandoId.set(null);
        this.exito.set(`Factura ${f.numero} generada — ${f.estado_display}`);
        programarAviso(this.destroyRef, () => this.exito.set(''), 4000);
        this.cargarFacturas();
        this.cargarVentas();
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al generar factura.');
        this.generandoId.set(null);
      },
    });
  }

  reintentar(factura: FacturaElectronica): void {
    this.accionId.set(factura.id);
    this.catalogo.reintentarFactura(factura.id).subscribe({
      next: () => {
        this.accionId.set(null);
        this.exito.set('Reintento procesado.');
        programarAviso(this.destroyRef, () => this.exito.set(''), 3000);
        this.cargarFacturas();
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al reintentar.');
        this.accionId.set(null);
      },
    });
  }

  reenviar(factura: FacturaElectronica): void {
    this.facturaReenviar.set(factura);
    this.reenviarVisible.set(true);
    this.emailReenvio = '';
    this.exitoReenvio.set('');
  }

  confirmarReenvio(): void {
    const f = this.facturaReenviar();
    if (!f) return;
    this.reenviando.set(true);
    this.catalogo.reenviarFactura(f.id, this.emailReenvio || undefined).subscribe({
      next: (r) => {
        this.reenviando.set(false);
        this.exitoReenvio.set(r.detalle);
        programarAviso(this.destroyRef, () => { this.reenviarVisible.set(false); this.exitoReenvio.set(''); }, 3000);
      },
      error: (e) => {
        this.exitoReenvio.set('');
        this.reenviando.set(false);
        this.error.set(e.detalle || 'Error al reenviar.');
      },
    });
  }

  verDetalle(factura: FacturaElectronica): void {
    this.detalleSeleccion.set(factura);
    this.detalleVisible.set(true);
  }

  crearNotaCredito(): void {
    if (!this.ventaNcSeleccionada || !this.motivoNc) return;
    this.creandoNc.set(true);
    this.error.set('');
    this.catalogo.crearNotaCredito(this.ventaNcSeleccionada, this.motivoNc).subscribe({
      next: (nc) => {
        this.creandoNc.set(false);
        this.exito.set(`Nota credito ${nc.numero} — ${nc.estado_display}`);
        programarAviso(this.destroyRef, () => this.exito.set(''), 4000);
        this.ventaNcSeleccionada = '';
        this.motivoNc = '';
        this.pestana.set('notas');
        this.cargarNotasCredito();
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al crear nota credito.');
        this.creandoNc.set(false);
      },
    });
  }
}
