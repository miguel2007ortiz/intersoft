/**
 * Inventario — movimientos de stock (Flujo 2)
 *
 * Que hace: muestra entradas, salidas y ajustes con su motivo, usuario y
 * fecha, y permite registrar un movimiento manual.
 * Ruta: /inventario (authGuard + personalGuard).
 * Por que asi: el inventario es un libro de movimientos, no un numero que se
 * edita. Cada cambio queda con autor y motivo, y el stock del producto es la
 * consecuencia de esos movimientos.
 */

import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoService } from '../../core/services/catalogo.service';
import { InventarioProducto, MovimientoInventario } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { MonedaPipe } from '../../core/pipes/moneda.pipe';
import { debounce } from '../../core/utils/temporizador.util';

@Component({
  selector: 'app-inventario',
  imports: [DatePipe, MonedaPipe, FormsModule, PanelShellComponent],
  templateUrl: './inventario.component.html',
  styleUrls: ['./inventario.component.css'],
})
export class InventarioComponent implements OnInit {
  private readonly catalogo = inject(CatalogoService);
  private readonly destroyRef = inject(DestroyRef);

  readonly productos = signal<InventarioProducto[]>([]);
  readonly movimientos = signal<MovimientoInventario[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly errorMovimientos = signal<string | null>(null);
  busquedaProducto = '';
  filtroStockBajo = false;
  /** Paginacion del listado (mismo patron que el catalogo de productos). */
  readonly pagina = signal(1);
  readonly totalPaginas = signal(1);
  readonly totalProductos = signal(0);
  readonly POR_PAGINA = 25;
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  readonly buscarProductosDebounced = debounce(this.destroyRef, () => this.cargarProductos(), 300);
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
    this.catalogo
      .listarInventario({
        busqueda: this.busquedaProducto || undefined,
        stock_bajo: this.filtroStockBajo || undefined,
        pagina: this.pagina(),
        limite: this.POR_PAGINA,
      })
      .subscribe({
        next: ({ resultados, total, total_paginas }) => {
          this.productos.set(resultados);
          this.totalProductos.set(total ?? 0);
          this.totalPaginas.set(total_paginas ?? 1);
          this.error.set(null);
          this.cargando.set(false);
        },
        error: (e) => {
          this.error.set(e.detalle ?? 'No se pudo cargar el inventario.');
          this.cargando.set(false);
        },
      });
  }

  buscarProductos(): void {
    this.pagina.set(1);
    this.buscarProductosDebounced();
  }

  irAPagina(p: number): void {
    if (p < 1 || p > this.totalPaginas()) return;
    this.pagina.set(p);
    this.cargarProductos();
  }

  cargarMovimientos(): void {
    this.catalogo.listarMovimientos().subscribe({
      next: (r) => {
        this.movimientos.set(r.resultados);
        this.errorMovimientos.set(null);
      },
      error: (e) =>
        this.errorMovimientos.set(e.detalle ?? 'No se pudieron cargar los movimientos.'),
    });
  }

  aplicarAjuste(): void {
    if (!this.ajusteProducto || !this.ajusteCantidad || !this.ajusteMotivo) return;

    this.cargandoAjuste.set(true);
    this.errorAjuste.set('');
    this.exitoAjuste.set('');

    this.catalogo
      .ajustarInventario({
        producto: this.ajusteProducto,
        cantidad: this.ajusteCantidad,
        tipo: this.ajusteTipo,
        motivo: this.ajusteMotivo,
      })
      .subscribe({
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
