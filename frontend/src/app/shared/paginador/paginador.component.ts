/**
 * Paginador — control de paginas de los listados del panel
 *
 * Que hace: muestra "Mostrando X-Y de N" y los botones de pagina anterior y
 * siguiente. No guarda estado: recibe los contadores que devuelve el backend y
 * emite la pagina pedida.
 * Donde se usa: Productos e Inventario (y cualquier listado que devuelva el
 * cuerpo de `core/paginacion.py`).
 * Por que asi: la pantalla dueña del listado es la que conserva la busqueda y
 * los filtros; el paginador solo dice "quiero la pagina N" y esa pantalla
 * vuelve a pedir con los filtros que ya tenia. Asi cambiar de pagina no puede
 * perder un filtro.
 */

import { Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-paginador',
  standalone: true,
  templateUrl: './paginador.component.html',
  styleUrls: ['./paginador.component.css'],
})
export class PaginadorComponent {
  /** Primer registro de la pagina (1-based). 0 si la pagina esta vacia. */
  readonly desde = input.required<number>();
  /** Ultimo registro de la pagina (1-based, inclusivo). 0 si esta vacia. */
  readonly hasta = input.required<number>();
  /** Registros que cumplen el filtro, NO los de esta pagina. */
  readonly total = input.required<number>();
  readonly pagina = input.required<number>();
  readonly totalPaginas = input.required<number>();
  /** Bloquea los botones mientras la peticion esta en vuelo. */
  readonly cargando = input(false);

  readonly cambiarPagina = output<number>();

  readonly hayAnterior = computed(() => this.pagina() > 1);
  readonly haySiguiente = computed(() => this.pagina() < this.totalPaginas());

  /** "Mostrando 51-100 de 1.024". Con la pagina vacia no se inventa un rango. */
  readonly resumen = computed(() => {
    const total = this.total().toLocaleString('es-CO');
    if (!this.total()) return 'Sin resultados';
    if (!this.hasta()) return `Sin resultados en esta pagina de ${total}`;
    return `Mostrando ${this.desde().toLocaleString('es-CO')}-${this.hasta().toLocaleString(
      'es-CO',
    )} de ${total}`;
  });

  anterior(): void {
    if (this.hayAnterior() && !this.cargando()) this.cambiarPagina.emit(this.pagina() - 1);
  }

  siguiente(): void {
    if (this.haySiguiente() && !this.cargando()) this.cambiarPagina.emit(this.pagina() + 1);
  }
}
