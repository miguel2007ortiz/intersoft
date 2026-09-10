/**
 * AuthShell — marco visual de las pantallas de sesion
 *
 * Que hace: pone el fondo, el logo y la tarjeta centrada donde viven login,
 * registro, recuperar y restablecer.
 * Donde se usa: envuelve el contenido de esas pantallas con <ng-content>.
 * Por que asi: separa el aspecto de la logica. Las pantallas de sesion solo
 * se ocupan de su formulario; si manana cambia la portada de acceso, se
 * cambia aqui una vez y no en cuatro sitios.
 */

import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BrilloCursorDirective } from '../../directives/brillo-cursor.directive';
import { SiteFooterComponent } from '../site-footer/site-footer.component';

@Component({
  selector: 'app-auth-shell',
  imports: [RouterLink, BrilloCursorDirective, SiteFooterComponent],
  templateUrl: './auth-shell.component.html',
  styleUrl: './auth-shell.component.css',
})
export class AuthShellComponent {}
