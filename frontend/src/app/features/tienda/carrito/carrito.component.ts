import { DecimalPipe } from '@angular/common';
import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { Carrito, CarritoItem, Cupon } from '../../../core/models/tienda.model';

@Component({
  selector: 'app-carrito',
  imports: [DecimalPipe, FormsModule, RouterLink],
  template: `
    <div class="carrito">
      <header class="carrito-header">
        <a routerLink="/catalogo" class="btn-volver">← Seguir comprando</a>
        <h1>Mi Carrito</h1>
      </header>

      @if (cargando()) {
        <div class="cargando">Cargando carrito...</div>
      } @else if (error()) {
        <div class="error-box">{{ error() }}</div>
      } @else if (!carrito() || !carrito()!.items.length) {
        <div class="vacio">
          <p>Tu carrito esta vacio.</p>
          <a routerLink="/catalogo" class="btn-seguir">Ver productos</a>
        </div>
      } @else {
        <section class="items">
          <table class="tabla">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Precio</th>
                <th>Cantidad</th>
                <th>Subtotal</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              @for (item of carrito()!.items; track item.id) {
                <tr>
                  <td>
                    <strong>{{ item.producto_nombre }}</strong>
                  </td>
                  <td>{{ item.producto_precio | number }} COP</td>
                  <td>
                    <div class="cantidad-control">
                      <button type="button" class="btn-cant"
                              [disabled]="item.cantidad <= 1"
                              (click)="cambiarCantidad(item, item.cantidad - 1)">−</button>
                      <span class="cant-valor">{{ item.cantidad }}</span>
                      <button type="button" class="btn-cant"
                              [disabled]="item.cantidad >= item.producto_stock"
                              (click)="cambiarCantidad(item, item.cantidad + 1)">+</button>
                    </div>
                    <span class="stock-label">Stock: {{ item.producto_stock }}</span>
                  </td>
                  <td class="subtotal">{{ item.subtotal | number }} COP</td>
                  <td>
                    <button type="button" class="btn-eliminar"
                            (click)="eliminarItem(item)">✕</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </section>

        <section class="cupon-seccion">
          <label>Cupon de descuento</label>
          @if (cuponAplicado()) {
            <div class="cupon-activo">
              <span>{{ cuponAplicado()!.codigo }} — {{ cuponAplicado()!.porcentaje }}% OFF</span>
              <button type="button" class="btn-quitar-cupon" (click)="quitarCupon()">✕</button>
            </div>
          } @else {
            <div class="cupon-input">
              <input type="text" placeholder="Codigo del cupon"
                     [(ngModel)]="codigoCupon" class="input" />
              <button type="button" class="btn-aplicar"
                      [disabled]="!codigoCupon || validandoCupon()"
                      (click)="aplicarCupon()">
                @if (validandoCupon()) { Validando... } @else { Aplicar }
              </button>
            </div>
            @if (errorCupon()) {
              <span class="error-cupon">{{ errorCupon() }}</span>
            }
          }
        </section>

        <section class="resumen">
          <div class="fila"><span>Subtotal</span><span>{{ carrito()!.subtotal | number }} COP</span></div>
          @if (Number(carrito()!.descuento) > 0) {
            <div class="fila descuento"><span>Descuento</span><span>-{{ carrito()!.descuento | number }} COP</span></div>
          }
          <div class="fila total"><span>Total</span><span>{{ carrito()!.total | number }} COP</span></div>
        </section>

        <section class="acciones">
          <button type="button" class="btn-checkout" (click)="irCheckout()">
            Proceder al checkout
          </button>
        </section>
      }
    </div>
  `,
  styles: [`
    .carrito { max-width: 800px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .carrito-header { margin-bottom: var(--e5); }
    .carrito-header h1 { margin: 8px 0 0; font-size: clamp(22px, 4vw, 28px); }
    .btn-volver {
      color: var(--primario); text-decoration: none; font-weight: 600; font-size: 14px;
    }
    .btn-volver:hover { text-decoration: underline; }

    .cargando, .vacio { text-align: center; padding: var(--e6); color: var(--gris); }
    .vacio p { font-size: 16px; margin-bottom: var(--e3); }
    .btn-seguir {
      display: inline-block; padding: 10px 24px; background: var(--primario); color: #fff;
      border-radius: 8px; text-decoration: none; font-weight: 600;
    }
    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 12px 16px; color: #b42318; font-size: 14px;
    }

    .tabla { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: var(--e4); }
    .tabla th { text-align: left; padding: 10px 8px; border-bottom: 2px solid var(--linea); font-weight: 600; }
    .tabla td { padding: 12px 8px; border-bottom: 1px solid var(--linea); }
    .subtotal { font-weight: 700; }
    .cantidad-control { display: inline-flex; align-items: center; gap: 0; border: 1px solid var(--linea); border-radius: 6px; overflow: hidden; }
    .btn-cant {
      width: 32px; height: 32px; border: 0; background: #f1f5f9; cursor: pointer;
      font-size: 16px; font-weight: 600;
    }
    .btn-cant:disabled { opacity: .4; cursor: not-allowed; }
    .cant-valor { width: 36px; text-align: center; font-weight: 600; }
    .stock-label { display: block; font-size: 11px; color: var(--gris); margin-top: 2px; }
    .btn-eliminax { border: 0; background: none; color: #b42318; cursor: pointer; font-size: 16px; padding: 4px 8px; }

    .cupon-seccion { margin-bottom: var(--e4); }
    .cupon-seccion label { display: block; font-weight: 600; margin-bottom: var(--e2); font-size: 14px; }
    .cupon-input { display: flex; gap: var(--e2); }
    .cupon-input .input { flex: 1; }
    .btn-aplicar {
      padding: 10px 18px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-size: 14px; font-weight: 600;
      cursor: pointer;
    }
    .btn-aplicar:disabled { opacity: .5; }
    .cupon-activo {
      display: flex; justify-content: space-between; align-items: center;
      background: #ecfdf3; border: 1px solid #d1fadf; border-radius: 8px;
      padding: 10px 14px; font-weight: 600; color: #067647;
    }
    .btn-quitar-cupon { border: 0; background: none; color: #b42318; cursor: pointer; font-size: 16px; }
    .error-cupon { display: block; margin-top: var(--e1); font-size: 13px; color: #b42318; }

    .resumen { text-align: right; margin-bottom: var(--e4); }
    .fila { display: flex; justify-content: space-between; padding: 6px 0; font-size: 15px; }
    .fila.descuento { color: #b42318; }
    .fila.total { font-size: 20px; font-weight: 700; border-top: 2px solid var(--linea); padding-top: 10px; margin-top: 4px; }

    .acciones { text-align: right; }
    .btn-checkout {
      padding: 12px 32px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-size: 15px;
      font-weight: 600; cursor: pointer;
    }
    .btn-checkout:hover { opacity: .9; }
  `],
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
      next: (c) => { this.carrito.set(c); this.cargando.set(false); },
      error: (e) => { this.error.set(e.detalle || 'Error al cargar.'); this.cargando.set(false); },
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
          error: (e) => { this.errorCupon.set(e.detalle || 'Error al aplicar.'); this.validandoCupon.set(false); },
        });
      },
      error: (e) => { this.errorCupon.set(e.detalle || 'Codigo invalido.'); this.validandoCupon.set(false); },
    });
  }

  quitarCupon(): void {
    this.tienda.aplicarCupon(null).subscribe({
      next: (c) => { this.carrito.set(c); this.cuponAplicado.set(null); this.codigoCupon = ''; },
      error: (e) => this.error.set(e.detalle || 'Error al quitar cupon.'),
    });
  }

  irCheckout(): void {
    this.router.navigate(['/checkout']);
  }
}
