import { Component, OnDestroy, inject, input, output, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

const CLAVE_COLAPSADO = 'intersoft.sidebar-colapsado';

/** Navegacion vertical de las paginas privadas. Solo enlaza rutas que
 * existen de verdad en app.routes.ts y respeta exactamente la misma
 * visibilidad por rol que ya tenia el menu anterior (fase 3):
 * Clientes/Productos ocultos para CLIENTE, Usuarios/Roles solo ADMINISTRADOR.
 *
 * Responsive:
 * - >=1024px: en linea, desplegable a mano (boton "Contraer/Expandir" al
 *   pie, se recuerda en localStorage). Por defecto expandido.
 * - <1024px: drawer fuera de pantalla controlado por [abierto]. Cuando
 *   esta cerrado queda `inert` para que no reciba foco de teclado
 *   mientras es invisible. */
@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css',
})
export class SidebarComponent implements OnDestroy {
  readonly auth = inject(AuthService);

  readonly abierto = input(false);
  readonly cerrar = output<void>();

  readonly colapsado = signal(
    typeof localStorage !== 'undefined' && localStorage.getItem(CLAVE_COLAPSADO) === '1',
  );

  private readonly mediaEscritorio =
    typeof matchMedia === 'function' ? matchMedia('(min-width: 1024px)') : null;
  readonly esEscritorio = signal(this.mediaEscritorio?.matches ?? true);
  private readonly detectarCambio = (evento: MediaQueryListEvent): void =>
    this.esEscritorio.set(evento.matches);

  constructor() {
    this.mediaEscritorio?.addEventListener('change', this.detectarCambio);
  }

  ngOnDestroy(): void {
    this.mediaEscritorio?.removeEventListener('change', this.detectarCambio);
  }

  alternarColapso(): void {
    this.colapsado.update((valor) => {
      const nuevo = !valor;
      localStorage.setItem(CLAVE_COLAPSADO, nuevo ? '1' : '0');
      return nuevo;
    });
  }
}
