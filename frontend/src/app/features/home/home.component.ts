import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BrilloCursorDirective } from '../../shared/directives/brillo-cursor.directive';
import { Inclinar3dDirective } from '../../shared/directives/inclinar-3d.directive';
import { RevelarAlEntrarDirective } from '../../shared/directives/revelar-al-entrar.directive';
import { SiteFooterComponent } from '../../shared/layout/site-footer/site-footer.component';

@Component({
  selector: 'app-home',
  imports: [RouterLink, BrilloCursorDirective, Inclinar3dDirective, RevelarAlEntrarDirective, SiteFooterComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent {
  readonly beneficios = [
    {
      icono: 'inventario',
      titulo: 'Inventario al dia',
      texto: 'Stock actualizado en cada venta y alertas cuando un producto llega al minimo.',
    },
    {
      icono: 'ventas',
      titulo: 'Ventas y facturacion',
      texto: 'Registra la venta en el mostrador y genera la factura en el mismo paso.',
    },
    {
      icono: 'tienda',
      titulo: 'Tienda virtual',
      texto: 'Tu catalogo en linea sincronizado con el inventario, sin conocimientos tecnicos.',
    },
    {
      icono: 'reportes',
      titulo: 'Reportes claros',
      texto: 'Cuanto vendiste, que se mueve y que esta quieto, sin cuadrar hojas de calculo.',
    },
  ];
}
