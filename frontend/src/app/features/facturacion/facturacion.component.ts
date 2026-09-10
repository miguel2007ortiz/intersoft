import { DatePipe, DecimalPipe, SlicePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoService } from '../../core/services/catalogo.service';
import { FacturaElectronica, NotaCredito, Venta } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { debounce, programarAviso } from '../../core/utils/temporizador.util';

@Component({
  selector: 'app-facturacion',
  imports: [DecimalPipe, SlicePipe, DatePipe, FormsModule, PanelShellComponent],
  templateUrl: './facturacion.component.html',
  styleUrls: ['./facturacion.component.css'],
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
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  readonly buscarFacturasDebounced = debounce(this.destroyRef, () => this.cargarFacturas(), 300);

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
    this.catalogo
      .listarFacturas({
        busqueda: this.busquedaFactura,
        estado: this.filtroEstado,
      })
      .subscribe({
        next: (r) => {
          this.facturas.set(r.resultados);
          this.cargando.set(false);
        },
        error: (e) => {
          this.error.set(e.detalle || 'Error al cargar.');
          this.cargando.set(false);
        },
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
        const ids = r.resultados.map((f) => f.venta);
        this.catalogo.listarVentas({ estado: 'completada' }).subscribe({
          next: (vr) => {
            this.ventasFacturadas.set(vr.resultados.filter((v) => ids.includes(v.id)));
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
      next: (r) => {
        this.notasCredito.set(r.resultados);
        this.cargandoNotas.set(false);
      },
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
        programarAviso(
          this.destroyRef,
          () => {
            this.reenviarVisible.set(false);
            this.exitoReenvio.set('');
          },
          3000,
        );
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
