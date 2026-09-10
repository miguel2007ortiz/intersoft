/**
 * SiteFooter — pie de las pantallas publicas
 *
 * Que hace: enlaces legales, contacto y aviso de derechos.
 * Donde se usa: marketplace y pantallas publicas.
 * Por que asi: separado del pie del panel interno, que no lleva contenido
 * comercial.
 */

import { Component } from '@angular/core';

/** Pie minimo y compartido por toda la app: nombre, tagline y copyright.
 * Se retiraron telefono, correo y redes sociales porque eran datos de
 * ejemplo sin destino real (ver AUDITORIA.md, seccion 9.2). */
@Component({
  selector: 'app-site-footer',
  templateUrl: './site-footer.component.html',
  styleUrls: ['./site-footer.component.css'],
})
export class SiteFooterComponent {}
