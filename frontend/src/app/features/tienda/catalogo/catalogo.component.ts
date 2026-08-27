import { DecimalPipe } from '@angular/common';
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { ProductoTienda, CategoriaTienda } from '../../../core/models/tienda.model';

@Component({
  selector: 'app-catalogo',
  imports: [DecimalPipe, FormsModule, RouterLink],
  template: `
    <div class="catalogo">
      <header class="catalogo-header">
        <h1>Tienda InterSoft</h1>
        <a routerLink="/carrito" class="btn-carrito">
          Carrito ({{ totalItems() }})
        </a>
      </header>

      <section class="filtros">
        <input type="text" placeholder="Buscar productos..."
               [(ngModel)]="busqueda" (input)="buscar()" class="input" />
        <select [(ngModel)]="categoriaSeleccionada" (change)="buscar()" class="input input-select">
          <option value="">Todas las categorias</option>
          @for (cat of categorias(); track cat.id) {
            <option [value]="cat.id">{{ cat.nombre }} ({{ cat.productos_count }})</option>
          }
        </select>
        <select [(ngModel)]="orden" (change)="buscar()" class="input input-select">
          <option value="nombre">Nombre</option>
          <option value="precio">Menor precio</option>
          <option value="-precio">Mayor precio</option>
          <option value="reciente">Mas recientes</option>
        </select>
      </section>

      @if (cargando()) {
        <div class="cargando">Cargando productos...</div>
      } @else if (error()) {
        <div class="error-box">{{ error() }}</div>
      } @else if (!productos().length) {
        <div class="vacio">No se encontraron productos.</div>
      } @else {
        <section class="grid">
          @for (p of productos(); track p.id) {
            <div class="card">
              <div class="card-img">
                @if (p.imagen) {
                  <img [src]="p.imagen" [alt]="p.nombre" />
                } @else {
                  <div class="placeholder-img">{{ p.nombre.charAt(0) }}</div>
                }
              </div>
              <div class="card-body">
                <span class="card-categoria">{{ p.categoria_nombre || 'Sin categoria' }}</span>
                <h3 class="card-nombre">{{ p.nombre }}</h3>
                <p class="card-sku">SKU: {{ p.sku }}</p>
                <div class="card-footer">
                  <span class="card-precio">\${{ p.precio | number }}</span>
                  @if (p.stock > 0) {
                    <button type="button" class="btn-agregar"
                            [disabled]="agregandoId() === p.id"
                            (click)="agregarAlCarrito(p)">
                      @if (agregandoId() === p.id) { Agregando... } @else { + Carrito }
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

      @if (exito()) {
        <div class="exito-toast">{{ exito() }}</div>
      }
    </div>
  `,
  styles: [`
    .catalogo { max-width: 1100px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .catalogo-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--e5); }
    .catalogo-header h1 { margin: 0; font-size: clamp(22px, 4vw, 28px); }
    .btn-carrito {
      padding: 8px 20px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-size: 14px;
      font-weight: 600; text-decoration: none; cursor: pointer;
    }
    .btn-carrito:hover { opacity: .9; }

    .filtros { display: flex; gap: var(--e3); flex-wrap: wrap; margin-bottom: var(--e5); }
    .input {
      padding: 10px 14px; border: 1px solid var(--linea);
      border-radius: 8px; font: inherit; font-size: 14px;
      background: #fff; transition: border-color .15s;
    }
    .input:focus { outline: none; border-color: var(--primario); }
    .input-select { min-width: 180px; }

    .cargando, .vacio { text-align: center; padding: var(--e6); color: var(--gris); font-size: 15px; }
    .error-box {
      background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px;
      padding: 12px 16px; margin-bottom: var(--e4); color: #b42318; font-size: 14px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: var(--e4);
    }
    .card {
      background: #fff; border: 1px solid var(--linea); border-radius: 12px;
      overflow: hidden; transition: box-shadow .2s;
    }
    .card:hover { box-shadow: 0 8px 24px rgba(15,23,42,.1); }
    .card-img { height: 160px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; }
    .card-img img { max-height: 100%; max-width: 100%; object-fit: contain; }
    .placeholder-img {
      width: 60px; height: 60px; border-radius: 50%;
      background: var(--primario); color: #fff; font-size: 24px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
    }
    .card-body { padding: 14px; }
    .card-categoria { font-size: 12px; color: var(--primario); font-weight: 600; text-transform: uppercase; }
    .card-nombre { margin: 6px 0 4px; font-size: 16px; }
    .card-sku { margin: 0 0 12px; font-size: 12px; color: var(--gris); }
    .card-footer { display: flex; justify-content: space-between; align-items: center; }
    .card-precio { font-size: 18px; font-weight: 700; color: var(--primario); }
    .btn-agregar {
      padding: 6px 14px; background: var(--primario); color: #fff;
      border: 0; border-radius: 6px; font: inherit; font-size: 13px;
      font-weight: 600; cursor: pointer;
    }
    .btn-agregar:hover { opacity: .9; }
    .btn-agregar:disabled { opacity: .5; cursor: not-allowed; }
    .sin-stock { font-size: 13px; color: #b42318; font-weight: 600; }

    .exito-toast {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      background: #067647; color: #fff; padding: 12px 24px;
      border-radius: 8px; font-size: 14px; font-weight: 600;
      box-shadow: 0 8px 24px rgba(6,118,71,.3);
    }
  `],
})
export class CatalogoComponent implements OnInit {
  private readonly tienda = inject(TiendaService);

  readonly productos = signal<ProductoTienda[]>([]);
  readonly categorias = signal<CategoriaTienda[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly agregandoId = signal<string | null>(null);
  readonly exito = signal('');

  busqueda = '';
  categoriaSeleccionada = '';
  orden = 'nombre';

  readonly totalItems = signal(0);

  ngOnInit(): void {
    this.cargarCatalogo();
    this.cargarCarrito();
  }

  cargarCatalogo(): void {
    this.cargando.set(true);
    this.tienda.listarCatalogo({
      busqueda: this.busqueda,
      categoria: this.categoriaSeleccionada,
      orden: this.orden,
    }).subscribe({
      next: (r) => {
        this.productos.set(r.resultados);
        this.categorias.set(r.categorias || []);
        this.cargando.set(false);
      },
      error: (e) => { this.error.set(e.detalle || 'Error al cargar.'); this.cargando.set(false); },
    });
  }

  buscar(): void {
    this.cargarCatalogo();
  }

  cargarCarrito(): void {
    this.tienda.obtenerCarrito().subscribe({
      next: (c) => this.totalItems.set(c.total_items),
      error: () => {},
    });
  }

  agregarAlCarrito(producto: ProductoTienda): void {
    this.agregandoId.set(producto.id);
    this.error.set('');
    this.tienda.agregarItem(producto.id, 1).subscribe({
      next: (c) => {
        this.totalItems.set(c.total_items);
        this.agregandoId.set(null);
        this.exito.set(`${producto.nombre} agregado al carrito`);
        setTimeout(() => this.exito.set(''), 3000);
      },
      error: (e) => { this.error.set(e.detalle || 'Error al agregar.'); this.agregandoId.set(null); },
    });
  }
}
