/**
 * Mis favoritos — productos guardados por el usuario
 *
 * Que hace: lista los favoritos, permite quitarlos con el corazon y anadirlos
 * al carrito directamente.
 * Ruta: /favoritos (authGuard).
 * Por que asi:
 *   - La API devuelve el favorito con el producto completo dentro
 *     (`producto_obj`), asi que la pantalla hace una sola peticion en vez de
 *     pedir despues cada producto por separado.
 *   - La animacion de entrada de las tarjetas la aporta la clase global
 *     `.aparecer`. Este componente NO declara su propia `animation` sobre la
 *     tarjeta: al hacerlo pisaba a la global y, al terminar, la tarjeta volvia
 *     al `opacity: 0` de base y los favoritos desaparecian a los 0,5 s.
 */

import { DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { AuthService } from '../../../core/services/auth.service';
import { ProductoTienda } from '../../../core/models/tienda.model';
import { programarAviso } from '../../../core/utils/temporizador.util';

@Component({
  selector: 'app-favoritos',
  imports: [DecimalPipe, RouterLink],
  templateUrl: './favoritos.component.html',
  styleUrls: ['./favoritos.component.css'],
})
export class FavoritosComponent implements OnInit {
  private readonly tienda = inject(TiendaService);
  private readonly auth = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);

  readonly productos = signal<ProductoTienda[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly agregandoId = signal<string | null>(null);
  readonly agregadoId = signal<string | null>(null);
  readonly exito = signal('');
  readonly imagenesFallidas = signal<Set<string>>(new Set());
  readonly esqueletos = [0, 1, 2, 3, 4, 5];

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set('');
    this.tienda.listarFavoritos().subscribe({
      next: (favoritos) => {
        this.productos.set(favoritos.map((f) => f.producto_obj));
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle || 'No se pudieron cargar los favoritos.');
        this.cargando.set(false);
      },
    });
  }

  quitar(producto: ProductoTienda): void {
    this.tienda.quitarFavorito(producto.id).subscribe({
      next: () => {
        this.productos.update((lista) => lista.filter((p) => p.id !== producto.id));
        this.exito.set(`${producto.nombre} eliminado de favoritos`);
        programarAviso(this.destroyRef, () => this.exito.set(''), 2500);
      },
      error: () => {
        this.error.set('No se pudo quitar el favorito.');
        programarAviso(this.destroyRef, () => this.error.set(''), 2500);
      },
    });
  }

  agregarAlCarrito(producto: ProductoTienda): void {
    if (!this.auth.estaAutenticado()) return;
    this.agregandoId.set(producto.id);
    this.tienda.agregarItem(producto.id, 1).subscribe({
      next: () => {
        this.agregandoId.set(null);
        this.agregadoId.set(producto.id);
        programarAviso(this.destroyRef, () => this.agregadoId.set(null), 1200);
        this.exito.set(`${producto.nombre} agregado al carrito`);
        programarAviso(this.destroyRef, () => this.exito.set(''), 2500);
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al agregar.');
        this.agregandoId.set(null);
        programarAviso(this.destroyRef, () => this.error.set(''), 3000);
      },
    });
  }

  marcarImagenFallida(productoId: string): void {
    this.imagenesFallidas.update((set) => new Set(set).add(productoId));
  }
}
