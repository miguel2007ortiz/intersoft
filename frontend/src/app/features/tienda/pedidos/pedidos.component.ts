/**
 * Mis pedidos — historial de compras del cliente
 *
 * Que hace: lista los pedidos con su estado (pagado, en preparacion, enviado)
 * y abre el detalle con los productos y el envio.
 * Ruta: /pedidos (authGuard).
 * Por que asi: el estado lo manda el backend ya traducido a texto para el
 * cliente; la pantalla no interpreta codigos internos del pedido.
 */

import { DecimalPipe, DatePipe } from '@angular/common';
import { Component, inject, signal, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { Pedido } from '../../../core/models/tienda.model';
import { EstadoVacioComponent } from '../../../shared/estado-vacio/estado-vacio.component';

@Component({
  selector: 'app-pedidos',
  imports: [DecimalPipe, DatePipe, RouterLink, EstadoVacioComponent],
  templateUrl: './pedidos.component.html',
  styleUrls: ['./pedidos.component.css'],
})
export class PedidosComponent implements OnInit {
  private readonly tienda = inject(TiendaService);
  private readonly router = inject(Router);

  readonly pedidos = signal<Pedido[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');

  Number = Number;

  verCatalogo(): void {
    this.router.navigate(['/catalogo']);
  }

  ngOnInit(): void {
    this.cargarPedidos();
  }

  cargarPedidos(): void {
    this.cargando.set(true);
    this.tienda.misPedidos().subscribe({
      next: (r) => {
        this.pedidos.set(r.resultados);
        this.error.set('');
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al cargar tus pedidos.');
        this.cargando.set(false);
      },
    });
  }
}
