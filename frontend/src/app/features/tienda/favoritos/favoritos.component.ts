import { DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { AuthService } from '../../../core/services/auth.service';
import { ProductoTienda } from '../../../core/models/tienda.model';
import { programarAviso } from '../../../core/utils/temporizador.util';

@Component({
  selector: 'app-favoritos',
  imports: [DecimalPipe, RouterLink],
  template: `
    <div class="favoritos">
      <header class="barra aparecer">
        <div class="contenedor barra-int">
          <a routerLink="/" class="logo"
            >Inter<span>Soft</span> <em class="logo-market">Marketplace</em></a
          >
          <nav class="acciones">
            <a routerLink="/catalogo" class="btn btn-secundario">Volver al catalogo</a>
            <a routerLink="/carrito" class="btn btn-primario">Ir al carrito</a>
          </nav>
        </div>
      </header>

      <main class="area aparecer">
        <div class="encabezado">
          <h1>Mis favoritos</h1>
          <p class="sub">Los productos que guardaste para comprar despues.</p>
        </div>

        @if (cargando()) {
          <section class="grid">
            @for (_ of esqueletos; track $index) {
              <div class="card card-esqueleto">
                <div class="skeleton skeleton-img"></div>
                <div class="skeleton skeleton-linea"></div>
                <div class="skeleton skeleton-linea corta"></div>
              </div>
            }
          </section>
        } @else if (error()) {
          <div class="error-box">{{ error() }}</div>
        } @else if (productos().length === 0) {
          <div class="vacio">
            <p class="vacio-icono">♥</p>
            <p>Aun no tienes productos favoritos.</p>
            <a routerLink="/catalogo" class="btn btn-primario">Explorar catalogo</a>
          </div>
        } @else {
          <section class="grid">
            @for (p of productos(); track p.id; let i = $index) {
              <div
                class="card tarjeta aparecer"
                [style.--retraso.ms]="(i % 12) * 60"
                (click)="agregarAlCarrito(p)"
                title="Click para agregar al carrito"
              >
                <div class="card-img">
                  @if (p.imagen && !imagenesFallidas().has(p.id)) {
                    <img
                      [src]="p.imagen"
                      [alt]="p.nombre"
                      loading="lazy"
                      (error)="marcarImagenFallida(p.id)"
                    />
                  } @else {
                    <div class="placeholder-img">{{ p.nombre.charAt(0) }}</div>
                  }
                  <button
                    type="button"
                    class="btn-corazon corazon-activo"
                    (click)="$event.stopPropagation(); quitar(p)"
                    aria-label="Quitar de favoritos"
                    title="Quitar de favoritos"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width="18"
                      height="18"
                      aria-hidden="true"
                      fill="currentColor"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M20.8 4.6a5.5 5.5 0 00-7.8 0L12 5.6l-1-1a5.5 5.5 0 00-7.8 7.8l1 1L12 21.2l7.8-7.8 1-1a5.5 5.5 0 000-7.8z"
                      />
                    </svg>
                  </button>
                </div>
                <div class="card-body">
                  <span class="card-categoria">{{ p.categoria_nombre || 'Sin categoria' }}</span>
                  <h3 class="card-nombre">{{ p.nombre }}</h3>
                  <p class="card-vendedor">Vendido por {{ p.empresa_nombre }}</p>
                  <div class="card-footer">
                    <span class="card-precio">{{ p.precio | number }} COP</span>
                    @if (p.stock > 0) {
                      <button
                        type="button"
                        class="btn-agregar"
                        [class.btn-agregar-ok]="agregadoId() === p.id"
                        [disabled]="agregandoId() === p.id"
                        (click)="$event.stopPropagation(); agregarAlCarrito(p)"
                      >
                        @if (agregandoId() === p.id) {
                          Agregando...
                        } @else if (agregadoId() === p.id) {
                          ¡Añadido!
                        } @else {
                          Carrito
                        }
                      </button>
                    } @else {
                      <span class="sin-stock">Sin stock</span>
                    }
                  </div>
                </div>
              </div>
            }
          </section>
        }
      </main>

      @if (exito()) {
        <div class="exito-toast">{{ exito() }}</div>
      }
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        min-height: 100vh;
        background: var(--fondo, #f8fafc);
        color: var(--tinta, #0f172a);
      }
      .barra {
        background: var(--superficie, #fff);
        border-bottom: 1px solid var(--linea, #e2e8f0);
      }
      .barra-int {
        max-width: 1100px;
        margin: 0 auto;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
      }
      .logo {
        font-weight: 800;
        color: var(--tinta, #0f172a);
        text-decoration: none;
        font-size: 20px;
      }
      .logo span {
        color: var(--primario, #2657d9);
      }
      .logo-market,
      .sub {
        color: var(--gris, #64748b);
      }
      .acciones {
        display: flex;
        gap: 10px;
        align-items: center;
      }
      .btn {
        padding: 9px 16px;
        border-radius: 8px;
        font: inherit;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition:
          opacity 0.15s,
          transform 0.1s;
        border: 1px solid var(--linea, #e2e8f0);
      }
      .btn:hover {
        transform: translateY(-1px);
      }
      .btn-primario {
        background: var(--primario, #2657d9);
        color: #fff;
        border-color: transparent;
      }
      .btn-primario:hover {
        opacity: 0.92;
      }
      .btn-secundario {
        background: var(--superficie, #fff);
        color: var(--tinta, #0f172a);
      }
      .area {
        max-width: 1100px;
        margin: 0 auto;
        padding: 28px 20px;
      }
      .encabezado {
        margin-bottom: 24px;
      }
      h1 {
        margin: 0 0 4px;
        font-size: 26px;
      }
      .sub {
        margin: 0;
        font-size: 14px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 20px;
      }
      .card {
        position: relative;
        background: var(--superficie, #fff);
        border: 1px solid var(--linea, #e2e8f0);
        border-radius: 12px;
        overflow: hidden;
      }
      .tarjeta {
        transition:
          transform 0.25s ease,
          box-shadow 0.25s ease;
        cursor: pointer;
        animation: entrar 0.5s ease backwards;
        animation-delay: var(--retraso, 0ms);
      }
      .tarjeta:hover {
        transform: translateY(-6px);
        box-shadow: 0 16px 32px rgba(15, 23, 42, 0.12);
      }
      @keyframes entrar {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: none;
        }
      }
      .card-img {
        position: relative;
        height: 160px;
        background: #f1f5f9;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
      }
      .card-img img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .placeholder-img {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: var(--primario, #2657d9);
        color: #fff;
        font-size: 22px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .btn-corazon {
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 6;
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #fff;
        color: #e11d48;
        border: 1px solid var(--linea);
        cursor: pointer;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.12);
        transition: transform 0.15s;
      }
      .btn-corazon:hover {
        transform: scale(1.1);
      }
      .card-body {
        padding: 14px;
      }
      .card-categoria {
        font-size: 12px;
        color: var(--primario, #2657d9);
        font-weight: 600;
        text-transform: uppercase;
      }
      .card-nombre {
        margin: 6px 0 2px;
        font-size: 16px;
      }
      .card-vendedor {
        margin: 0 0 10px;
        font-size: 12.5px;
        color: var(--gris, #64748b);
      }
      .card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .card-precio {
        font-size: 18px;
        font-weight: 700;
        color: var(--primario, #2657d9);
      }
      .btn-agregar {
        display: inline-flex;
        align-items: center;
        padding: 6px 14px;
        background: var(--primario, #2657d9);
        color: #fff;
        border: 0;
        border-radius: 6px;
        font: inherit;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition:
          opacity 0.15s,
          transform 0.1s;
      }
      .btn-agregar:hover {
        opacity: 0.9;
      }
      .btn-agregar:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .btn-agregar-ok {
        background: #067647;
      }
      .sin-stock {
        font-size: 13px;
        color: #b42318;
        font-weight: 600;
      }
      .vacio {
        text-align: center;
        padding: 48px 20px;
        color: var(--gris, #64748b);
      }
      .vacio-icono {
        font-size: 40px;
        color: #e11d48;
        margin: 0 0 8px;
      }
      .vacio .btn {
        margin-top: 16px;
      }
      .error-box {
        background: #fef3f2;
        border: 1px solid #fecdca;
        border-radius: 8px;
        padding: 12px 16px;
        color: #b42318;
        font-size: 14px;
      }
      .exito-toast {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #067647;
        color: #fff;
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
        z-index: 100;
      }
      .card-esqueleto {
        pointer-events: none;
      }
      .skeleton {
        background: #eef1f5;
        border-radius: 6px;
      }
      .skeleton-img {
        height: 160px;
        border-radius: 0;
      }
      .skeleton-linea {
        height: 14px;
        margin: 14px;
      }
      .skeleton-linea.corta {
        width: 60%;
      }
      @media (max-width: 640px) {
        .barra-int {
          flex-direction: column;
          align-items: flex-start;
        }
      }
    `,
  ],
})
export class FavoritosComponent {
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
      next: (c) => {
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
