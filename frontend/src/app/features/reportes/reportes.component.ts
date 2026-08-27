import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { AnalyticsService } from '../../core/services/analytics.service';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { ErrorCatalogo } from '../../core/models/catalogo.model';
import {
  CategoriaFiltro, DatosReporte, FiltrosAnalitica, TipoReporte,
} from '../../core/models/analytics.model';

/** Fase 7: generacion y exportacion de reportes (solo ADMINISTRADOR).
 * Las exportaciones se hacen sin librerias: Excel = CSV con BOM, PDF = HTML
 * de impresion que el navegador guarda como PDF. */

interface ColumnaCol { clave: string; nombre: string; }

@Component({
  selector: 'app-reportes',
  imports: [FormsModule, PanelShellComponent],
  templateUrl: './reportes.component.html',
  styleUrl: './reportes.component.css',
})
export class ReportesComponent {
  readonly auth = inject(AuthService);
  private readonly analytics = inject(AnalyticsService);

  readonly tipos = signal<TipoReporte[]>([]);
  readonly categorias = signal<CategoriaFiltro[]>([]);
  readonly datos = signal<DatosReporte | null>(null);

  readonly tipoSel = signal('');
  readonly fechaInicio = signal('');
  readonly fechaFin = signal('');
  readonly categoriaSel = signal('');

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  /** Columnas del reporte seleccionado para la tabla (claves legibles). */
  readonly columnas = computed<ColumnaCol[]>(() =>
    (this.datos()?.columnas ?? []).map(([clave, nombre]) => ({ clave, nombre })),
  );

  readonly esAdmin = computed(() => this.auth.esAdministrador());

  constructor() {
    this.analytics.tiposReporte().subscribe({
      next: (r) => {
        this.tipos.set(r.resultados);
        if (r.resultados.length > 0) this.tipoSel.set(r.resultados[0].tipo);
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'Error al cargar los reportes.'),
    });
    this.analytics.categorias().subscribe({
      next: (r) => this.categorias.set(r.resultados),
    });
  }

  private filtros(): FiltrosAnalitica {
    return {
      fecha_inicio: this.fechaInicio() || undefined,
      fecha_fin: this.fechaFin() || undefined,
      categoria: this.categoriaSel() || undefined,
    };
  }

  verReporte(): void {
    if (!this.tipoSel()) return;
    this.cargando.set(true);
    this.error.set(null);
    this.analytics.verReporte(this.tipoSel(), this.filtros()).subscribe({
      next: (r) => this.datos.set(r),
      error: (e: ErrorCatalogo) => {
        this.error.set(e.detalle ?? 'No se pudo generar el reporte.');
        this.cargando.set(false);
      },
      complete: () => this.cargando.set(false),
    });
  }

  /** Abre la descarga en una pestaña nueva (El servidor fija Content-Disposition). */
  exportar(formato: 'excel' | 'pdf'): void {
    if (!this.tipoSel()) return;
    window.open(this.analytics.exportarUrl(this.tipoSel(), formato, this.filtros()), '_blank');
  }

  esNumero(valor: string | number | null | undefined): boolean {
    return typeof valor === 'number';
  }

  dinero(valor: string | number | null | undefined): string {
    const n = Number(valor ?? 0);
    return n.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
  }

  numero(valor: string | number | null | undefined): string {
    const n = Number(valor ?? 0);
    return n.toLocaleString('es-CO', { maximumFractionDigits: 0 });
  }

  formatearCelda(fila: Record<string, string | number>, clave: string): string {
    const valor = fila[clave];
    if (typeof valor === 'number') {
      // Las columnas de dinero e ingresos resaltan el valor con moneda.
      const claveBaja = clave.toLowerCase();
      if (claveBaja.includes('ingreso') || claveBaja.includes('total')
        || claveBaja.includes('valor') || claveBaja.includes('comprado')) {
        return this.dinero(valor);
      }
      return this.numero(valor);
    }
    return String(valor ?? '');
  }

  esMoneda(clave: string): boolean {
    const c = clave.toLowerCase();
    return c.includes('ingreso') || c.includes('total')
      || c.includes('valor') || c.includes('comprado') || c.includes('rotacion');
  }
}
