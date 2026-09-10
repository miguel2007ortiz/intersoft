import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CatalogoService } from '../../core/services/catalogo.service';
import { Venta } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { EstadoVacioComponent } from '../../shared/estado-vacio/estado-vacio.component';
import { debounce } from '../../core/utils/temporizador.util';

@Component({
  selector: 'app-ventas',
  imports: [
    DatePipe,
    DecimalPipe,
    FormsModule,
    RouterLink,
    PanelShellComponent,
    EstadoVacioComponent,
  ],
  templateUrl: './ventas.component.html',
  styleUrls: ['./ventas.component.css'],
})
export class VentasComponent implements OnInit {
  private readonly catalogo = inject(CatalogoService);
  private readonly destroyRef = inject(DestroyRef);

  readonly ventas = signal<Venta[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  busqueda = '';
  filtroEstado = '';
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  readonly buscarDebounced = debounce(this.destroyRef, () => this.cargarVentas(), 300);
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
    this.catalogo
      .listarVentas({
        estado: this.filtroEstado || undefined,
        busqueda: this.busqueda || undefined,
      })
      .subscribe({
        next: (r) => {
          this.ventas.set(r.resultados);
          const est = r.estadisticas as
            { total_ventas: string; total_registros: number } | undefined;
          this.estadisticas.set(est ?? null);
          this.error.set(null);
          this.cargando.set(false);
        },
        error: (e) => {
          this.error.set(e.detalle ?? 'No se pudo cargar la lista.');
          this.cargando.set(false);
        },
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
