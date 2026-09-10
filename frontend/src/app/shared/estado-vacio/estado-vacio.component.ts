/**
 * EstadoVacio — mensaje cuando una lista no tiene nada que mostrar
 *
 * Que hace: icono, titulo, texto y boton opcional de accion.
 * Donde se usa: cualquier tabla o rejilla sin resultados.
 * Por que asi: una tabla vacia sin explicacion parece un error de carga. Este
 * componente distingue "no hay nada todavia" de "tu busqueda no encontro nada"
 * y ofrece el siguiente paso.
 */

import { Component, input, output } from '@angular/core';

export type TipoEstadoVacio = 'vacio' | 'error' | 'busqueda';

/**
 * Estado reutilizable de una seccion sin datos o con fallo de carga.
 * Unifica el "estado vacio", el de "busqueda sin resultados" y el de
 * "error con reintento" que antes se repetia en cada pantalla del panel y
 * de la tienda (clientes, productos, ventas, pedidos, favoritos, carrito).
 */
@Component({
  selector: 'app-estado-vacio',
  standalone: true,
  templateUrl: './estado-vacio.component.html',
  styleUrls: ['./estado-vacio.component.css'],
})
export class EstadoVacioComponent {
  readonly tipo = input<TipoEstadoVacio>('vacio');
  readonly titulo = input<string | null>(null);
  readonly mensaje = input<string | null>(null);
  readonly accionTexto = input<string | null>(null);
  readonly accion = output<void>();
}
