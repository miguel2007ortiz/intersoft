import { Component, inject, input, output } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

/** Barra superior de las paginas privadas: logo, nombre de la empresa (tenant),
 * usuario con su rol y cerrar sesion. En movil expone el boton que abre el
 * drawer del sidebar (ver SidebarComponent). Busqueda y notificaciones
 * quedan fuera de esta fase. */
@Component({
  selector: 'app-topbar',
  imports: [RouterLink],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.css',
})
export class TopbarComponent {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Estado del drawer movil, controlado por el padre (PanelShellComponent). */
  readonly menuAbierto = input(false);
  readonly alternarMenu = output<void>();

  salir(): void {
    this.auth.cerrarSesion();
    this.router.navigate(['/login']);
  }
}
