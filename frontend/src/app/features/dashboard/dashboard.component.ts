import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { CatalogoService } from '../../core/services/catalogo.service';
import { Producto } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

/** Resumen del dia. Stock bajo y valor de inventario se calculan de verdad
 * a partir de /api/productos/ (ya existe). Ventas y facturas todavia no
 * tienen API en el backend (ver AUDITORIA.md, seccion 4): en vez de
 * mostrar un "$0" que pareceria un dato real, se marcan como "sin datos
 * aun" para no confundir "no hay ventas" con "no se puede saber". */
@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, PanelShellComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent {
  readonly auth = inject(AuthService);
  private readonly catalogo = inject(CatalogoService);

  readonly cargandoInventario = signal(true);
  readonly productosStockBajo = signal<Producto[]>([]);
  readonly valorInventario = signal(0);

  /** Clientes/Productos (y por tanto estas metricas) son del personal
   * interno: mismo criterio que ya usan el sidebar y el personalGuard. */
  readonly tieneInventario = computed(() => this.auth.usuario()?.rol !== 'CLIENTE');

  constructor() {
    if (this.tieneInventario()) {
      this.catalogo.listarProductos({ activo: true }).subscribe({
        next: ({ resultados }) => {
          this.productosStockBajo.set(resultados.filter((p) => p.stock_bajo));
          this.valorInventario.set(
            resultados.reduce((suma, p) => suma + Number(p.precio) * p.stock, 0),
          );
          this.cargandoInventario.set(false);
        },
        error: () => this.cargandoInventario.set(false),
      });
    } else {
      this.cargandoInventario.set(false);
    }
  }

  /** "Daniel Velasco Ruiz" -> "Daniel" (mismo criterio que WelcomeOverlayComponent) */
  primerNombre(): string {
    return (this.auth.usuario()?.nombre ?? '').trim().split(' ')[0] || 'de nuevo';
  }

  formatearValor(valor: number): string {
    return valor.toLocaleString('es-CO', { maximumFractionDigits: 0 });
  }
}
