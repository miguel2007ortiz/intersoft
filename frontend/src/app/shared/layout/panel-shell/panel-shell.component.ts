/**
 * PanelShell — marco de todas las pantallas del panel interno
 *
 * Que hace: coloca la sidebar, la topbar y el area de contenido donde entra
 * cada pantalla via <ng-content>.
 * Donde se usa: envuelve las pantallas de los Flujos 2 y 3.
 * Por que asi: el menu y la cabecera se escriben una sola vez. Cada pantalla se
 * ocupa solo de su contenido, y un cambio de navegacion se hace en un archivo.
 */

import { Component, HostListener, signal } from '@angular/core';
import { BrilloCursorDirective } from '../../directives/brillo-cursor.directive';
import { SiteFooterComponent } from '../site-footer/site-footer.component';
import { TopbarComponent } from '../topbar/topbar.component';
import { SidebarComponent } from '../sidebar/sidebar.component';

/** Layout comun de las paginas privadas (equivalente a un "base.html" en
 * este proyecto Angular): topbar + sidebar de navegacion + contenido de
 * altura completa + pie. Usar asi:
 * <app-panel-shell> ...contenido... </app-panel-shell>, y si la pagina
 * necesita algo extra en la cabecera, marcarlo con el atributo panelHeader
 * (se proyecta al inicio del <main>). */
@Component({
  selector: 'app-panel-shell',
  imports: [BrilloCursorDirective, SiteFooterComponent, TopbarComponent, SidebarComponent],
  templateUrl: './panel-shell.component.html',
  styleUrls: ['./panel-shell.component.css'],
})
export class PanelShellComponent {
  readonly menuMovilAbierto = signal(false);

  alternarMenuMovil(): void {
    this.menuMovilAbierto.update((abierto) => !abierto);
  }

  cerrarMenuMovil(): void {
    this.menuMovilAbierto.set(false);
  }

  @HostListener('document:keydown.escape')
  cerrarConEscape(): void {
    this.menuMovilAbierto.set(false);
  }
}
