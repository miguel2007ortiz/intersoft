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
  template: `
    <div class="estado" [class]="tipo()" role="status" [attr.aria-live]="tipo() === 'error' ? 'assertive' : 'polite'">
      <svg class="icono" viewBox="0 0 24 24" width="48" height="48" aria-hidden="true">
        @switch (tipo()) {
          @case ('error') {
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <path d="M12 8v5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="16.2" r="1.1" fill="currentColor"/>
          }
          @case ('busqueda') {
            <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <line x1="16" y1="16" x2="20" y2="20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          }
          @case ('vacio') {
            <rect x="5" y="4" width="14" height="17" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <line x1="9" y1="9" x2="15" y2="9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            <line x1="9" y1="13" x2="15" y2="13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          }
        }
      </svg>

      @if (titulo(); as t) {
        <p class="titulo">{{ t }}</p>
      }
      @if (mensaje(); as m) {
        <p class="mensaje">{{ m }}</p>
      }
      @if (accionTexto(); as a) {
        <button type="button" class="accion" (click)="accion.emit()">{{ a }}</button>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    .estado {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      text-align: center; padding: var(--e6) var(--e4); gap: var(--e2);
      color: var(--gris);
    }
    .estado.error { color: #b42318; }
    .estado.error .mensaje { color: #b42318; }
    .icono { opacity: .55; margin-bottom: var(--e1); }
    .titulo { margin: 0; font-size: 15px; font-weight: 700; color: inherit; }
    .mensaje { margin: 0; font-size: 14px; max-width: 46ch; }
    .accion {
      margin-top: var(--e2);
      padding: 8px 18px; border: 1px solid var(--linea); background: #fff;
      border-radius: 8px; cursor: pointer; font: inherit; font-size: 13px; font-weight: 600;
      color: var(--texto);
    }
    .error .accion { color: #b42318; }
    .accion:hover { border-color: var(--primario); color: var(--primario); }
  `],
})
export class EstadoVacioComponent {
  readonly tipo = input<TipoEstadoVacio>('vacio');
  readonly titulo = input<string | null>(null);
  readonly mensaje = input<string | null>(null);
  readonly accionTexto = input<string | null>(null);
  readonly accion = output<void>();
}