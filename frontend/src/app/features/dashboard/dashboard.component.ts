import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { AnalyticsService } from '../../core/services/analytics.service';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { ErrorCatalogo } from '../../core/models/catalogo.model';
import {
  CategoriaFiltro, ClienteFrecuente, FiltrosAnalitica, ResumenDashboard,
  SeriesVentas, TopProducto, ValorPorCategoria,
} from '../../core/models/analytics.model';

/** Fase 7: panel de analitica (solo ADMINISTRADOR). Consulta las vistas SQL
 * del backend y dibuja graficas SVG puras (sin librerias externas), con
 * filtros de rango de fechas y categoria que refrescan sin recargar. */

interface PuntoBarra {
  etiqueta: string;
  valor: number;
}

@Component({
  selector: 'app-dashboard',
  imports: [FormsModule, RouterLink, PanelShellComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent {
  readonly auth = inject(AuthService);
  private readonly analytics = inject(AnalyticsService);

  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  readonly resumen = signal<ResumenDashboard | null>(null);
  readonly series = signal<SeriesVentas | null>(null);
  readonly topProductos = signal<TopProducto[]>([]);
  readonly clientes = signal<ClienteFrecuente[]>([]);
  readonly valorCategorias = signal<ValorPorCategoria[]>([]);
  readonly categorias = signal<CategoriaFiltro[]>([]);

  readonly fechaInicio = signal('');
  readonly fechaFin = signal('');
  readonly categoriaSel = signal('');

  /** Solo los ADMINISTRADOR ven el dashboard de analitica. */
  readonly esAdmin = computed(() => this.auth.esAdministrador());

  constructor() {
    this.categorias().length; // inicializa (carga dentro de reload)
    this.cargarTodo();
  }

  /** Aplica los filtros y recarga todas las metricas. */
  cargarTodo(): void {
    const filtros: FiltrosAnalitica = {
      fecha_inicio: this.fechaInicio() || undefined,
      fecha_fin: this.fechaFin() || undefined,
      categoria: this.categoriaSel() || undefined,
    };
    this.cargando.set(true);
    this.error.set(null);

    // Categorias (para el filtro) se cargan una sola vez.
    if (this.categorias().length === 0) {
      this.analytics.categorias().subscribe({
        next: (r) => this.categorias.set(r.resultados),
      });
    }

    this.analytics.resumen(filtros).subscribe({
      next: (r) => this.resumen.set(r),
      error: (e: ErrorCatalogo) => {
        this.error.set(e.detalle ?? 'Error al cargar el resumen.');
        this.cargando.set(false);
      },
      complete: () => this.cargando.set(false),
    });

    this.analytics.ventas(filtros).subscribe({
      next: (r) => this.series.set(r),
      error: () => {},
    });

    this.analytics.topProductos(filtros).subscribe({
      next: (r) => this.topProductos.set(r.resultados.slice(0, 8)),
      error: () => {},
    });

    this.analytics.clientesFrecuentes(filtros).subscribe({
      next: (r) => this.clientes.set(r.resultados.slice(0, 6)),
      error: () => {},
    });

    this.analytics.inventario().subscribe({
      next: (r) => this.valorCategorias.set(r.valor_por_categoria),
      error: () => {},
    });
  }

  // ----------------------- Helpers de formato ------------------------------
  dinero(valor: number | null | undefined): string {
    return `${(valor ?? 0).toLocaleString('es-CO', { maximumFractionDigits: 0 })} COP`;
  }

  numero(valor: number | null | undefined): string {
    return (valor ?? 0).toLocaleString('es-CO', { maximumFractionDigits: 0 });
  }

  primerNombre(): string {
    return (this.auth.usuario()?.nombre ?? '').trim().split(' ')[0] || 'de nuevo';
  }

  // ----------------------- Series para las graficas ------------------------
  /** Barras de ventas por dia (utiliza la serie diaria). */
  barrasDia(): PuntoBarra[] {
    return (this.series()?.por_dia ?? []).map((p) => ({
      etiqueta: p.dia.slice(8) + '/' + p.dia.slice(5, 7), // DD/MM
      valor: p.ingresos,
    }));
  }

  /** Barras horizontales del valor de inventario por categoria. */
  barrasInventario(): ValorPorCategoria[] {
    return this.valorCategorias().slice(0, 8);
  }

  maximoInventario(): number {
    return Math.max(1, ...this.valorCategorias().map((c) => c.valor));
  }

  // ----------------------- SVG (grafica de barras) -------------------------
  /** Ancho del area de dibujo (coord. viewBox). */
  anchoSvg = 560;
  altoSvg = 220;
  margenInf = 26;
  margenSup = 10;

  private maxBarra(): number {
    const valores = this.barrasDia().map((b) => b.valor);
    return Math.max(1, ...valores);
  }

  /** Altura en px/cord de cada barra dentro del area de dibujo. */
  alturaBarra(punto: PuntoBarra, indice: number): number {
    void indice;
    const usable = this.altoSvg - this.margenInf - this.margenSup;
    return Math.max(1, (punto.valor / this.maxBarra()) * usable);
  }

  /** Posicion Y (tope superior) de una barra. */
  yBarra(punto: PuntoBarra, indice: number): number {
    return this.altoSvg - this.margenInf - this.alturaBarra(punto, indice);
  }

  /** Posicion X (centro) de cada barra, distribuidas uniformemente. */
  xCentro(indice: number, total: number): number {
    const usable = this.anchoSvg;
    if (total <= 1) return usable / 2;
    return (usable * (indice + 0.5)) / total;
  }

  anchoBarra(total: number): number {
    if (total <= 1) return this.anchoSvg * 0.5;
    return Math.min(46, (this.anchoSvg / total) * 0.55);
  }
}
