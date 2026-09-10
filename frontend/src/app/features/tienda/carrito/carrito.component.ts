/**
 * Carrito — revision de la compra antes de pagar
 *
 * Que hace: lista los items, cambia cantidades, quita productos, aplica cupon
 * y muestra subtotal, descuento y total.
 * Ruta: /carrito (authGuard).
 * Por que asi: los totales los calcula y devuelve el backend en cada cambio;
 * el frontend no suma por su cuenta para que el precio que ve el cliente sea
 * exactamente el que se va a cobrar. Cambiar la cantidad manda solo la nueva
 * cantidad: el producto ya lo sabe el item del carrito.
 */

import { DecimalPipe } from '@angular/common';
import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { Carrito, CarritoItem, Cupon } from '../../../core/models/tienda.model';

@Component({
  selector: 'app-carrito',
  imports: [DecimalPipe, FormsModule, RouterLink],
  templateUrl: './carrito.component.html',
  styleUrls: ['./carrito.component.css'],
})
export class CarritoComponent implements OnInit {
  private readonly tienda = inject(TiendaService);
  private readonly router = inject(Router);

  readonly carrito = signal<Carrito | null>(null);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly exito = signal('');
  readonly cuponAplicado = signal<Cupon | null>(null);
  readonly validandoCupon = signal(false);
  readonly errorCupon = signal('');

  codigoCupon = '';

  Number = Number;

  ngOnInit(): void {
    this.cargarCarrito();
  }

  cargarCarrito(): void {
    this.cargando.set(true);
    this.tienda.obtenerCarrito().subscribe({
      next: (c) => {
        this.carrito.set(c);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al cargar.');
        this.cargando.set(false);
      },
    });
  }

  cambiarCantidad(item: CarritoItem, nuevaCantidad: number): void {
    this.tienda.actualizarItem(item.id, nuevaCantidad).subscribe({
      next: (c) => this.carrito.set(c),
      error: (e) => this.error.set(e.detalle || 'Error al actualizar.'),
    });
  }

  eliminarItem(item: CarritoItem): void {
    this.tienda.eliminarItem(item.id).subscribe({
      next: (c) => this.carrito.set(c),
      error: (e) => this.error.set(e.detalle || 'Error al eliminar.'),
    });
  }

  aplicarCupon(): void {
    if (!this.codigoCupon) return;
    this.validandoCupon.set(true);
    this.errorCupon.set('');
    this.tienda.validarCodigo(this.codigoCupon).subscribe({
      next: (cupon) => {
        this.tienda.aplicarCupon(cupon.id).subscribe({
          next: (c) => {
            this.carrito.set(c);
            this.cuponAplicado.set(cupon);
            this.validandoCupon.set(false);
          },
          error: (e) => {
            this.errorCupon.set(e.detalle || 'Error al aplicar.');
            this.validandoCupon.set(false);
          },
        });
      },
      error: (e) => {
        this.errorCupon.set(e.detalle || 'Codigo invalido.');
        this.validandoCupon.set(false);
      },
    });
  }

  quitarCupon(): void {
    this.tienda.aplicarCupon(null).subscribe({
      next: (c) => {
        this.carrito.set(c);
        this.cuponAplicado.set(null);
        this.codigoCupon = '';
      },
      error: (e) => this.error.set(e.detalle || 'Error al quitar cupon.'),
    });
  }

  irCheckout(): void {
    this.router.navigate(['/checkout']);
  }
}
