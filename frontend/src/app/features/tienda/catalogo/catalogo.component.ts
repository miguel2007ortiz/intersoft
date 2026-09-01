import { DecimalPipe } from '@angular/common';
import { Component, ElementRef, inject, signal, computed, OnInit, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { AuthService } from '../../../core/services/auth.service';
import { ProductoTienda, CategoriaTienda } from '../../../core/models/tienda.model';
import { BrilloCursorDirective } from '../../../shared/directives/brillo-cursor.directive';
import { RevelarAlEntrarDirective } from '../../../shared/directives/revelar-al-entrar.directive';

@Component({
  selector: 'app-catalogo',
  imports: [DecimalPipe, FormsModule, RouterLink, BrilloCursorDirective, RevelarAlEntrarDirective],
  template: `
    <div class="catalogo">
      <header class="barra aparecer">
        <div class="contenedor barra-int">
          <a routerLink="/" class="logo">Inter<span>Soft</span> <em class="logo-market">Marketplace</em></a>

          <div class="buscador">
            <svg class="buscador-icono" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
            <input #campoBusqueda type="text" placeholder="Buscar productos..." [(ngModel)]="busqueda"
                   (keyup.enter)="buscar()" (input)="onBusquedaInput()" class="input" />
            <button type="button" class="btn-buscar" (click)="buscar()">Buscar</button>
          </div>

          <nav class="acciones">
            @if (sesion(); as u) {
              <div class="cuenta">
                <span class="cuenta-nombre">{{ u.nombre }}</span>
                <a routerLink="/pedidos" class="btn btn-secundario btn-sm">Mis pedidos</a>
                <button type="button" class="btn btn-secundario btn-sm" (click)="salir()">Salir</button>
              </div>
            } @else {
              <a routerLink="/login" class="btn btn-secundario">Iniciar sesion</a>
              <a routerLink="/registro-comprador" class="btn btn-primario">Registrarse</a>
            }
            <a routerLink="/carrito" class="btn-carrito">
              Carrito ({{ totalItems() }})
            </a>
          </nav>
        </div>
      </header>

      <section class="hero" appBrilloCursor>
        <span class="orbe-fondo orbe-a"></span>
        <span class="orbe-fondo orbe-b"></span>
        <div class="contenedor hero-int">
          <p class="etiqueta aparecer insignia-pulso">Empresas verificadas y activas</p>
          <h1 class="aparecer" style="--retraso: 90ms">
            Compra directo a las empresas<br /><span class="resaltado">que ya conoces y confias</span>
          </h1>
          <p class="entrada aparecer" style="--retraso: 180ms">
            Un solo lugar para explorar el catalogo de tus proveedores favoritos, comparar precios
            y hacer seguimiento a tu pedido de principio a fin.
          </p>
          <div class="hero-acciones aparecer" style="--retraso: 270ms">
            <button type="button" class="btn btn-primario" (click)="irAlCatalogo()">Explorar catalogo</button>
            @if (!sesion()) {
              <a routerLink="/registro-comprador" class="btn btn-secundario">Crear cuenta gratis</a>
            }
          </div>
        </div>
      </section>

      <section class="confianza" appRevelarAlEntrar>
        <div class="contenedor confianza-grilla">
          <div class="confianza-item">
            <span class="confianza-icono" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                   stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" />
                <path d="M9.5 12l1.8 1.8L15 10.2" />
              </svg>
            </span>
            <span>Empresas registradas y verificadas</span>
          </div>
          <div class="confianza-item">
            <span class="confianza-icono" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                   stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <path d="M7 11V7a5 5 0 0110 0v4" />
              </svg>
            </span>
            <span>Compra segura con tu cuenta</span>
          </div>
          <div class="confianza-item">
            <span class="confianza-icono" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                   stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 4h2l2.5 12h9L20 8H7" />
                <circle cx="10" cy="20" r="1.4" />
                <circle cx="17" cy="20" r="1.4" />
              </svg>
            </span>
            <span>Seguimiento de tu pedido en linea</span>
          </div>
          <div class="confianza-item">
            <span class="confianza-icono" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                   stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 11.5a8.4 8.4 0 01-8.4 8.4H4l2.2-3.3A8.4 8.4 0 1121 11.5Z" />
              </svg>
            </span>
            <span>Atencion directa del vendedor</span>
          </div>
        </div>
      </section>

      <section class="filtros aparecer" style="--retraso: 80ms">
        <div class="chips">
          <button type="button" class="chip" [class.chip-activo]="!categoriaSeleccionada"
                  (click)="filtrarPorCategoria('')">Todas</button>
          @for (cat of categorias(); track cat.id) {
            <button type="button" class="chip" [class.chip-activo]="categoriaSeleccionada === cat.id"
                    (click)="filtrarPorCategoria(cat.id)">
              {{ cat.nombre }} <span class="chip-cuenta">{{ cat.productos_count }}</span>
            </button>
          }
        </div>
        <select [(ngModel)]="orden" (change)="buscar()" class="input input-select">
          <option value="nombre">Nombre</option>
          <option value="precio">Menor precio</option>
          <option value="-precio">Mayor precio</option>
          <option value="reciente">Mas recientes</option>
        </select>
      </section>

      <section class="area-tienda">
        @if (cargando()) {
          <section class="grid" aria-hidden="true">
            @for (i of esqueletos; track i) {
              <div class="card card-esqueleto">
                <div class="skeleton skeleton-img"></div>
                <div class="card-body">
                  <div class="skeleton skeleton-linea" style="width: 40%"></div>
                  <div class="skeleton skeleton-linea" style="width: 80%"></div>
                  <div class="skeleton skeleton-linea" style="width: 50%"></div>
                </div>
              </div>
            }
          </section>
        } @else if (error()) {
          <div class="error-box">{{ error() }}</div>
        } @else if (!productos().length) {
          <div class="vacio">No se encontraron productos.</div>
        } @else {
          <section class="grid">
            @for (p of productos(); track p.id; let i = $index) {
              <div class="card tarjeta-flot aparecer" [style.--retraso.ms]="(i % 12) * 60">
                <div class="card-img">
                  @if (p.imagen) {
                    <img [src]="p.imagen" [alt]="p.nombre" />
                  } @else {
                    <div class="placeholder-img">{{ p.nombre.charAt(0) }}</div>
                  }
                  @if (p.stock > 0 && p.stock <= 5) {
                    <span class="badge badge-urgencia">¡Ultimas {{ p.stock }}!</span>
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
                              [class.btn-agregar-ok]="agregadoId() === p.id"
                              [disabled]="agregandoId() === p.id"
                              (click)="agregarAlCarrito(p)">
                        @if (agregandoId() === p.id) {
                          Agregando...
                        } @else if (agregadoId() === p.id) {
                          ✓ Agregado
                        } @else {
                          + Carrito
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

          @if (totalPaginas() > 1) {
            <nav class="paginador aparecer">
              <button type="button" class="btn-paginador" [disabled]="pagina() <= 1"
                      (click)="irPagina(pagina() - 1)">&larr; Anterior</button>
              <span class="paginador-info">Pagina {{ pagina() }} de {{ totalPaginas() }}</span>
              <button type="button" class="btn-paginador" [disabled]="pagina() >= totalPaginas()"
                      (click)="irPagina(pagina() + 1)">Siguiente &rarr;</button>
            </nav>
          }
        }
      </section>

      @if (exito()) {
        <div class="exito-toast">{{ exito() }}</div>
      }

      <section class="llamado" appRevelarAlEntrar>
        <div class="contenedor llamado-int">
          <div>
            <h2>¿Tienes un negocio?</h2>
            <p>Suma tu catalogo a InterSoft y llega a compradores listos para comprar hoy.</p>
          </div>
          <a routerLink="/registro" class="btn btn-primario">Registrar mi negocio</a>
        </div>
      </section>

      <footer class="pie">
        <span>InterSoft Marketplace</span>
      </footer>
    </div>
  `,
  styles: [`
    .catalogo { min-height: 100vh; background: var(--papel); }

    .barra {
      position: sticky; top: 0; z-index: 500;
      background: rgba(255,255,255,.92); backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--linea); padding: var(--e3) 0;
    }
    .barra-int { display: flex; align-items: center; gap: var(--e4); }
    .logo { font-size: 22px; font-weight: 700; color: var(--tinta); text-decoration: none; white-space: nowrap; }
    .logo span { color: var(--primario); }
    .logo-market { font-style: normal; font-size: 12px; color: var(--gris); font-weight: 600; margin-left: 4px; }

    .buscador { position: relative; display: flex; flex: 1; gap: var(--e2); min-width: 180px; }
    .buscador .input { flex: 1; padding-left: 38px; }
    .buscador-icono {
      position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
      width: 18px; height: 18px; color: var(--gris); pointer-events: none;
    }
    .btn-buscar {
      padding: 10px 18px; background: var(--primario); color: #fff; border: 0;
      border-radius: 8px; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer;
    }
    .btn-buscar:hover { opacity: .9; }

    .acciones { display: flex; align-items: center; gap: var(--e3); }
    .cuenta { display: flex; align-items: center; gap: var(--e2); }
    .cuenta-nombre { font-size: 14px; font-weight: 600; color: var(--tinta); max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .btn-sm { padding: 6px 12px; font-size: 13px; }
    .btn-carrito {
      padding: 8px 18px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-size: 14px;
      font-weight: 600; text-decoration: none; cursor: pointer; white-space: nowrap;
    }
    .btn-carrito:hover { opacity: .9; }

    .hero {
      position: relative; overflow: hidden; padding: var(--e7) 0 var(--e6);
      background: var(--primario-suave); --brillo-x: 50%; --brillo-y: 30%;
    }
    .hero::before {
      content: ''; position: absolute; inset: 0; pointer-events: none;
      background: radial-gradient(420px circle at var(--brillo-x) var(--brillo-y), rgba(38,87,217,.16), transparent 70%);
    }
    .hero-int { position: relative; z-index: 1; text-align: center; max-width: 1100px; margin: 0 auto; padding: 0 var(--e4); }
    .orbe-a { width: 320px; height: 320px; top: -80px; left: -60px; }
    .orbe-b { width: 260px; height: 260px; bottom: -100px; right: -40px; animation-delay: 1.2s; }
    .etiqueta {
      display: inline-block; background: #fff; border: 1px solid var(--linea); border-radius: 999px;
      padding: var(--e1) var(--e4); font-size: 13.5px; font-weight: 600; color: var(--primario-osc); margin: 0 0 var(--e4);
    }
    .hero h1 { font-size: clamp(26px, 4.5vw, 40px); line-height: 1.2; margin: 0 0 var(--e4); }
    .resaltado { color: var(--primario-osc); }
    .entrada { max-width: 560px; margin: 0 auto var(--e5); color: var(--gris); font-size: 16px; }
    .hero-acciones { display: flex; gap: var(--e3); justify-content: center; flex-wrap: wrap; }

    .confianza { border-bottom: 1px solid var(--linea); background: #fff; }
    .confianza-grilla {
      display: grid; gap: var(--e4); grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      max-width: 1100px; margin: 0 auto; padding: var(--e4); width: 100%;
    }
    .confianza-item { display: flex; align-items: center; gap: var(--e2); font-size: 13.5px; font-weight: 600; color: var(--tinta); }
    .confianza-icono {
      display: grid; place-items: center; width: 34px; height: 34px; flex-shrink: 0;
      border-radius: 10px; background: var(--primario-suave); color: var(--primario-osc);
    }
    .confianza-icono svg { width: 18px; height: 18px; }

    .filtros {
      display: flex; gap: var(--e3); flex-wrap: wrap; align-items: flex-start; justify-content: space-between;
      padding: var(--e5) var(--e4) 0; max-width: 1100px; margin: 0 auto; width: 100%;
    }
    .chips { display: flex; gap: 8px; flex-wrap: wrap; flex: 1; }
    .chip {
      display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px;
      border: 1px solid var(--linea); border-radius: 999px; background: #fff;
      font: inherit; font-size: 13.5px; font-weight: 600; color: var(--tinta);
      cursor: pointer; transition: border-color .15s, background .15s, color .15s, transform .15s;
    }
    .chip:hover { border-color: var(--primario); color: var(--primario-osc); transform: translateY(-1px); }
    .chip-activo { background: var(--primario); border-color: var(--primario); color: #fff; }
    .chip-activo:hover { color: #fff; }
    .chip-cuenta { opacity: .75; font-weight: 500; }

    .area-tienda { max-width: 1100px; margin: 0 auto; padding: var(--e5) var(--e4); }

    .input {
      padding: 10px 14px; border: 1px solid var(--linea);
      border-radius: 8px; font: inherit; font-size: 14px;
      background: #fff; transition: border-color .15s;
    }
    .input:focus { outline: none; border-color: var(--primario); }
    .input-select { min-width: 180px; }

    .cargando, .vacio { text-align: center; padding: var(--e7); color: var(--gris); font-size: 15px; }
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
      overflow: hidden;
    }
    .card-img {
      position: relative; height: 160px; background: #f1f5f9; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
    }
    .card-img img { max-height: 100%; max-width: 100%; object-fit: contain; transition: transform .35s ease; }
    .card:hover .card-img img { transform: scale(1.08); }
    .placeholder-img {
      width: 60px; height: 60px; border-radius: 50%;
      background: var(--primario); color: #fff; font-size: 24px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
    }
    .badge {
      position: absolute; top: 8px; left: 8px; padding: 4px 9px; border-radius: 999px;
      font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em;
    }
    .badge-urgencia { background: #fef3f2; color: #b42318; border: 1px solid #fecdca; }
    .card-body { padding: 14px; }
    .card-categoria { font-size: 12px; color: var(--primario); font-weight: 600; text-transform: uppercase; }
    .card-nombre { margin: 6px 0 4px; font-size: 16px; }
    .card-sku { margin: 0 0 12px; font-size: 12px; color: var(--gris); }
    .card-footer { display: flex; justify-content: space-between; align-items: center; }
    .card-precio { font-size: 18px; font-weight: 700; color: var(--primario); }
    .btn-agregar {
      padding: 6px 14px; background: var(--primario); color: #fff;
      border: 0; border-radius: 6px; font: inherit; font-size: 13px;
      font-weight: 600; cursor: pointer; transition: opacity .15s, transform .1s, background .2s;
    }
    .btn-agregar:hover { opacity: .9; }
    .btn-agregar:active { transform: scale(.94); }
    .btn-agregar:disabled { opacity: .5; cursor: not-allowed; }
    .btn-agregar-ok { background: #067647; }
    .sin-stock { font-size: 13px; color: #b42318; font-weight: 600; }

    /* Esqueletos de carga (shimmer) mientras llega el catalogo */
    .card-esqueleto { pointer-events: none; }
    .skeleton {
      position: relative; overflow: hidden; background: #eef1f5; border-radius: 6px;
    }
    .skeleton::after {
      content: ''; position: absolute; inset: 0; transform: translateX(-100%);
      background: linear-gradient(90deg, transparent, rgba(255,255,255,.7), transparent);
      animation: brillo-esqueleto 1.4s ease-in-out infinite;
    }
    .skeleton-img { height: 160px; border-radius: 0; }
    .skeleton-linea { height: 12px; margin: 8px 14px; }
    @keyframes brillo-esqueleto { to { transform: translateX(100%); } }

    .paginador {
      display: flex; align-items: center; justify-content: center; gap: var(--e4);
      margin-top: var(--e6); padding-top: var(--e5); border-top: 1px solid var(--linea);
    }
    .btn-paginador {
      padding: 8px 16px; background: #fff; border: 1px solid var(--linea);
      border-radius: 8px; font: inherit; font-size: 13.5px; font-weight: 600;
      color: var(--tinta); cursor: pointer; transition: border-color .15s, color .15s;
    }
    .btn-paginador:hover:not(:disabled) { border-color: var(--primario); color: var(--primario-osc); }
    .btn-paginador:disabled { opacity: .4; cursor: not-allowed; }
    .paginador-info { font-size: 13.5px; color: var(--gris); }

    .llamado { padding: var(--e7) 0; background: var(--primario-suave); border-top: 1px solid var(--linea); }
    .llamado-int {
      display: flex; align-items: center; justify-content: space-between; gap: var(--e5); flex-wrap: wrap;
      max-width: 1100px; margin: 0 auto; padding: 0 var(--e4);
    }
    .llamado h2 { margin: 0 0 var(--e1); font-size: 22px; }
    .llamado p { margin: 0; color: var(--gris); }

    .pie { text-align: center; padding: var(--e5) var(--e4); color: var(--gris); font-size: 13px; }

    .exito-toast {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      background: #067647; color: #fff; padding: 12px 24px;
      border-radius: 8px; font-size: 14px; font-weight: 600;
      box-shadow: 0 8px 24px rgba(6,118,71,.3);
      animation: entrar-toast .35s cubic-bezier(.22,1,.36,1);
    }
    @keyframes entrar-toast {
      from { opacity: 0; transform: translateY(12px) scale(.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @media (prefers-reduced-motion: reduce) {
      .card-img img, .btn-agregar, .chip { transition: none; }
      .card:hover .card-img img { transform: none; }
      .skeleton::after { animation: none; }
      .exito-toast { animation: none; }
    }

    @media (max-width: 700px) {
      .barra-int { flex-wrap: wrap; }
      .buscador { order: 3; flex-basis: 100%; }
      .llamado-int { justify-content: center; text-align: center; }
    }
  `],
})
export class CatalogoComponent implements OnInit {
  private readonly tienda = inject(TiendaService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly sesion = this.auth.usuario;

  readonly productos = signal<ProductoTienda[]>([]);
  readonly categorias = signal<CategoriaTienda[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly agregandoId = signal<string | null>(null);
  readonly agregadoId = signal<string | null>(null);
  readonly exito = signal('');

  busqueda = '';
  categoriaSeleccionada = '';
  orden = 'nombre';

  readonly totalItems = signal(0);
  readonly pagina = signal(1);
  readonly totalPaginas = signal(1);
  /** Cantidad de tarjetas fantasma mientras carga el catalogo. */
  readonly esqueletos = Array.from({ length: 8 }, (_, i) => i);

  private busquedaTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly campoBusqueda = viewChild<ElementRef<HTMLInputElement>>('campoBusqueda');

  /** Boton del hero: lleva el foco al buscador para invitar a explorar. */
  irAlCatalogo(): void {
    this.campoBusqueda()?.nativeElement.focus();
    document.querySelector('.filtros')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

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
      pagina: String(this.pagina()),
    }).subscribe({
      next: (r) => {
        this.productos.set(r.resultados);
        this.categorias.set(r.categorias || []);
        this.totalPaginas.set(r.total_paginas || 1);
        this.cargando.set(false);
      },
      error: (e) => { this.error.set(e.detalle || 'Error al cargar.'); this.cargando.set(false); },
    });
  }

  /** Busqueda/filtro nuevo: siempre vuelve a la pagina 1. */
  buscar(): void {
    this.pagina.set(1);
    this.cargarCatalogo();
  }

  /** Debounce de 350ms para no disparar una request en cada tecla. */
  onBusquedaInput(): void {
    if (this.busquedaTimer) clearTimeout(this.busquedaTimer);
    this.busquedaTimer = setTimeout(() => this.buscar(), 350);
  }

  filtrarPorCategoria(categoriaId: string): void {
    this.categoriaSeleccionada = categoriaId;
    this.buscar();
  }

  irPagina(nueva: number): void {
    if (nueva < 1 || nueva > this.totalPaginas()) return;
    this.pagina.set(nueva);
    this.cargarCatalogo();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cargarCarrito(): void {
    this.tienda.obtenerCarrito().subscribe({
      next: (c) => this.totalItems.set(c.total_items),
      error: () => {},
    });
  }

  agregarAlCarrito(producto: ProductoTienda): void {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/login'], { queryParams: { redirigir: '/' } });
      return;
    }
    this.agregandoId.set(producto.id);
    this.error.set('');
    this.tienda.agregarItem(producto.id, 1).subscribe({
      next: (c) => {
        this.totalItems.set(c.total_items);
        this.agregandoId.set(null);
        this.agregadoId.set(producto.id);
        setTimeout(() => this.agregadoId.set(null), 1200);
        this.exito.set(`${producto.nombre} agregado al carrito`);
        setTimeout(() => this.exito.set(''), 3000);
      },
      error: (e) => { this.error.set(e.detalle || 'Error al agregar.'); this.agregandoId.set(null); },
    });
  }

  salir(): void {
    this.auth.cerrarSesion();
  }
}
