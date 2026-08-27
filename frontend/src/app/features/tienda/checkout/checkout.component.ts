import { DecimalPipe } from '@angular/common';
import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { Carrito, CheckoutResponse, StockInsuficiente } from '../../../core/models/tienda.model';

@Component({
  selector: 'app-checkout',
  imports: [DecimalPipe, FormsModule, RouterLink],
  template: `
    <div class="checkout">
      <header class="checkout-header">
        <a routerLink="/carrito" class="btn-volver">← Volver al carrito</a>
        <h1>Checkout</h1>
      </header>

      @if (cargando()) {
        <div class="cargando">Procesando compra...</div>
      } @else if (exito()) {
        <div class="exito-box">
          <div class="exito-icono">✓</div>
          <h2>Compra realizada exitosamente</h2>
          <p>Factura: <strong>{{ exito()!.numero_factura }}</strong></p>
          <p>Total: <strong>\${{ exito()!.total | number }}</strong></p>
          <p class="transaccion">Transaccion: {{ exito()!.transaccion_id }}</p>
          <div class="exito-acciones">
            <a routerLink="/catalogo" class="btn-seguir">Seguir comprando</a>
            <a routerLink="/ventas" class="btn-ventas">Ver historial de ventas</a>
          </div>
        </div>
      } @else {
        @if (error()) {
          <div class="error-box">{{ error() }}</div>
        }
        @if (erroresStock().length) {
          <div class="error-box">
            <strong>Stock insuficiente:</strong>
            @for (e of erroresStock(); track e.producto) {
              <div>{{ e.producto_nombre }}: solicita {{ e.solicitado }}, disponible {{ e.disponible }}</div>
            }
          </div>
        }

        <section class="resumen">
          <h2>Resumen de la compra</h2>
          @if (carrito()) {
            <div class="resumen-items">
              @for (item of carrito()!.items; track item.id) {
                <div class="resumen-item">
                  <span>{{ item.producto_nombre }} × {{ item.cantidad }}</span>
                  <span>\${{ item.subtotal | number }}</span>
                </div>
              }
            </div>
            <div class="resumen-totales">
              <div class="fila"><span>Subtotal</span><span>\${{ carrito()!.subtotal | number }}</span></div>
              @if (Number(carrito()!.descuento) > 0) {
                <div class="fila descuento"><span>Descuento</span><span>-\${{ carrito()!.descuento | number }}</span></div>
              }
              <div class="fila total"><span>Total a pagar</span><span>\${{ carrito()!.total | number }}</span></div>
            </div>
          }
        </section>

        <section class="metodo-pago">
          <label>Metodo de pago</label>
          <div class="metodos">
            @for (m of metodosPago; track m.valor) {
              <button type="button"
                      [class.activo]="metodoPago() === m.valor"
                      (click)="metodoPago.set(m.valor)"
                      class="btn-metodo">
                {{ m.etiqueta }}
              </button>
            }
          </div>
        </section>

        <section class="acciones">
          <button type="button" class="btn-pagar"
                  [disabled]="cargando()"
                  (click)="procesarPago()">
            @if (cargando()) { Procesando... } @else { Pagar \${{ carrito()?.total | number }}
            }
          </button>
        </section>
      }
    </div>
  `,
  styles: [`
    .checkout { max-width: 600px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .checkout-header { margin-bottom: var(--e5); }
    .checkout-header h1 { margin: 8px 0 0; font-size: clamp(22px, 4vw, 28px); }
    .btn-volver { color: var(--primario); text-decoration: none; font-weight: 600; font-size: 14px; }
    .btn-volver:hover { text-decoration: underline; }

    .cargando { text-align: center; padding: var(--e6); color: var(--gris); font-size: 15px; }
    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 12px 16px; margin-bottom: var(--e4); color: #b42318; font-size: 14px;
    }
    .error-box strong { display: block; margin-bottom: 4px; }

    .resumen { margin-bottom: var(--e5); }
    .resumen h2 { font-size: 18px; margin: 0 0 var(--e3); }
    .resumen-items { border: 1px solid var(--linea); border-radius: 8px; overflow: hidden; margin-bottom: var(--e3); }
    .resumen-item {
      display: flex; justify-content: space-between; padding: 10px 14px;
      font-size: 14px; border-bottom: 1px solid var(--linea);
    }
    .resumen-item:last-child { border-bottom: 0; }
    .resumen-totales { text-align: right; }
    .fila { display: flex; justify-content: space-between; padding: 6px 0; font-size: 15px; }
    .fila.descuento { color: #b42318; }
    .fila.total { font-size: 20px; font-weight: 700; border-top: 2px solid var(--linea); padding-top: 10px; margin-top: 4px; }

    .metodo-pago { margin-bottom: var(--e5); }
    .metodo-pago label { display: block; font-weight: 600; margin-bottom: var(--e2); font-size: 14px; }
    .metodos { display: flex; gap: var(--e2); flex-wrap: wrap; }
    .btn-metodo {
      padding: 10px 18px; border: 1px solid var(--linea); border-radius: 8px;
      background: #fff; cursor: pointer; font: inherit; font-size: 14px;
      transition: all .15s;
    }
    .btn-metodo:hover { border-color: var(--primario); }
    .btn-metodo.activo { background: var(--primario); color: #fff; border-color: var(--primario); }

    .acciones { text-align: right; }
    .btn-pagar {
      padding: 14px 40px; background: #067647; color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-size: 16px;
      font-weight: 700; cursor: pointer; transition: opacity .15s;
    }
    .btn-pagar:hover { opacity: .9; }
    .btn-pagar:disabled { opacity: .5; cursor: not-allowed; }

    .exito-box {
      background: #ecfdf3; border: 1px solid #d1fadf; border-radius: 12px;
      padding: 32px; text-align: center; color: #067647;
    }
    .exito-icono {
      width: 60px; height: 60px; border-radius: 50%; background: #067647;
      color: #fff; font-size: 28px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto var(--e3);
    }
    .exito-box h2 { margin: 0 0 var(--e3); color: #067647; }
    .exito-box p { margin: 4px 0; font-size: 15px; }
    .transaccion { font-size: 13px; color: var(--gris); margin-top: var(--e2) !important; }
    .exito-acciones { margin-top: var(--e4); display: flex; gap: var(--e3); justify-content: center; }
    .btn-seguir, .btn-ventas {
      padding: 10px 20px; border-radius: 8px; text-decoration: none;
      font-weight: 600; font-size: 14px;
    }
    .btn-seguir { background: var(--primario); color: #fff; }
    .btn-ventas { border: 1px solid var(--linea); color: var(--texto); }
  `],
})
export class CheckoutComponent implements OnInit {
  private readonly tienda = inject(TiendaService);
  private readonly router = inject(Router);

  readonly carrito = signal<Carrito | null>(null);
  readonly cargando = signal(false);
  readonly error = signal('');
  readonly exito = signal<CheckoutResponse | null>(null);
  readonly erroresStock = signal<StockInsuficiente[]>([]);
  readonly metodoPago = signal('tarjeta');

  readonly metodosPago = [
    { valor: 'efectivo', etiqueta: 'Efectivo' },
    { valor: 'transferencia', etiqueta: 'Transferencia' },
    { valor: 'nequi', etiqueta: 'Nequi' },
    { valor: 'daviplata', etiqueta: 'Daviplata' },
    { valor: 'tarjeta', etiqueta: 'Tarjeta' },
  ];

  Number = Number;

  ngOnInit(): void {
    this.cargarCarrito();
  }

  cargarCarrito(): void {
    this.tienda.obtenerCarrito().subscribe({
      next: (c) => {
        if (!c.items.length) {
          this.router.navigate(['/catalogo']);
          return;
        }
        this.carrito.set(c);
      },
      error: () => this.router.navigate(['/catalogo']),
    });
  }

  procesarPago(): void {
    this.cargando.set(true);
    this.error.set('');
    this.erroresStock.set([]);

    this.tienda.checkout(this.metodoPago()).subscribe({
      next: (r) => { this.exito.set(r); this.cargando.set(false); },
      error: (e) => {
        if (e.codigo === 'STOCK_INSUFICIENTE') {
          this.erroresStock.set(e.productos || []);
        } else {
          this.error.set(e.detalle || 'Error al procesar el pago.');
        }
        this.cargando.set(false);
      },
    });
  }
}
