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
