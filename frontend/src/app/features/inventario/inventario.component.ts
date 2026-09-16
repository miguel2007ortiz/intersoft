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

import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoService } from '../../core/services/catalogo.service';
import { InventarioProducto, MovimientoInventario } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { PaginadorComponent } from '../../shared/paginador/paginador.component';
import { debounce } from '../../core/utils/temporizador.util';

@Component({
  selector: 'app-inventario',
  imports: [DatePipe, DecimalPipe, FormsModule, PanelShellComponent, PaginadorComponent],
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
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  readonly buscarProductosDebounced = debounce(
    this.destroyRef,
    () => {
      // Un filtro nuevo cambia el conjunto: seguir en la pagina 3 dejaria la
      // tabla vacia sin explicacion.
      this.pagina.set(1);
      this.cargarProductos();
    },
    300,
  );
  /** Contadores del backend para el paginador (BUG-24, mismo cuerpo que
   * /api/productos/). `total` son los registros que cumplen el filtro. */
  readonly pagina = signal(1);
  readonly totalPaginas = signal(1);
  readonly total = signal(0);
  readonly desde = signal(0);
  readonly hasta = signal(0);
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
        // Los dos filtros viajan juntos al servidor: combinarlos en el cliente
        // sobre la pagina ya recortada solo miraria los 50 primeros productos.
        busqueda: this.busquedaProducto || undefined,
        stock_bajo: this.filtroStockBajo || undefined,
        pagina: this.pagina(),
      })
      .subscribe({
        next: (r) => {
          this.productos.set(r.resultados);
          this.total.set(r.total ?? 0);
          this.pagina.set(r.pagina ?? 1);
          this.totalPaginas.set(r.total_paginas ?? 1);
          this.desde.set(r.desde ?? 0);
          this.hasta.set(r.hasta ?? 0);
          this.error.set(null);
          this.cargando.set(false);
        },
        error: (e) => {
          this.error.set(e.detalle ?? 'No se pudo cargar el inventario.');
          this.cargando.set(false);
        },
      });
  }

  /** Marcar o desmarcar "Solo stock bajo" cambia el conjunto: vuelve a la
   * primera pagina, como la busqueda. */
  filtrarStockBajo(): void {
    this.pagina.set(1);
    this.cargarProductos();
  }

  irAPagina(numero: number): void {
    this.pagina.set(numero);
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
