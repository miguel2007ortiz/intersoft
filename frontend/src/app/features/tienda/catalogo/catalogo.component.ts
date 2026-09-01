import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, ElementRef, inject, signal, computed, OnInit, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { AuthService } from '../../../core/services/auth.service';
import { ProductoTienda, CategoriaTienda, ComentarioProducto } from '../../../core/models/tienda.model';
import { BrilloCursorDirective } from '../../../shared/directives/brillo-cursor.directive';
import { RevelarAlEntrarDirective } from '../../../shared/directives/revelar-al-entrar.directive';

@Component({
  selector: 'app-catalogo',
  imports: [DatePipe, DecimalPipe, FormsModule, RouterLink, BrilloCursorDirective, RevelarAlEntrarDirective],
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
              <svg class="btn-carrito-icono" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="9" cy="21" r="1" />
                <circle cx="20" cy="21" r="1" />
                <path d="M1 1h4l2.7 13.4a2 2 0 002 1.6h9.7a2 2 0 002-1.6L23 6H6" />
              </svg>
              Carrito
              <span class="btn-carrito-contador" [class.rebote]="carritoAnimado()">{{ totalItems() }}</span>
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
              <div class="card tarjeta-flot tarjeta-hover aparecer" [style.--retraso.ms]="(i % 12) * 60"
                   (dblclick)="abrirDetalle(p)" title="Doble click para ver el detalle">
                <div class="card-img">
                  @if (p.imagen && !imagenesFallidas().has(p.id)) {
                    <img [src]="p.imagen" [alt]="p.nombre" loading="lazy" (error)="marcarImagenFallida(p.id)" />
                  } @else {
                    <div class="placeholder-img">{{ p.nombre.charAt(0) }}</div>
                  }
                  <div class="card-badges">
                    @if (p.stock > 0 && p.stock <= 5) {
                      <span class="badge badge-urgencia">¡Ultimas {{ p.stock }}!</span>
                    }
                    @if (esTopCalificado(p)) {
                      <span class="badge badge-top">★ Top calificado</span>
                    }
                    @if (esNuevo(p)) {
                      <span class="badge badge-nuevo">Nuevo</span>
                    }
                  </div>
                </div>
                <div class="card-body">
                  <span class="card-categoria">{{ p.categoria_nombre || 'Sin categoria' }}</span>
                  <h3 class="card-nombre">{{ p.nombre }}</h3>
                  @if (p.total_comentarios > 0) {
                    <p class="card-calificacion">
                      <span class="estrellas-mini">{{ estrellasTexto(redondear(p.promedio_calificacion)) }}</span>
                      {{ p.promedio_calificacion }} <span class="gris">({{ p.total_comentarios }})</span>
                    </p>
                  } @else {
                    <p class="card-calificacion gris">Sin calificaciones aun</p>
                  }
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
                          <svg class="icono-check" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                               stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <path d="M20 6L9 17l-5-5" />
                          </svg>
                          ¡Añadido!
                        } @else {
                          <svg class="icono-carrito" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                               stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <circle cx="9" cy="21" r="1" />
                            <circle cx="20" cy="21" r="1" />
                            <path d="M1 1h4l2.7 13.4a2 2 0 002 1.6h9.7a2 2 0 002-1.6L23 6H6" />
                          </svg>
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

      @if (productoDetalle(); as p) {
        <div class="modal-fondo" (click)="cerrarDetalle()">
          <div class="modal-caja" role="dialog" aria-modal="true" [attr.aria-label]="p.nombre"
               (click)="$event.stopPropagation()">
            <button type="button" class="modal-cerrar" (click)="cerrarDetalle()" aria-label="Cerrar">✕</button>

            <div class="detalle">
              <div class="detalle-img">
                @if (p.imagen && !imagenesFallidas().has(p.id)) {
                  <img [src]="p.imagen" [alt]="p.nombre" (error)="marcarImagenFallida(p.id)" />
                } @else {
                  <div class="placeholder-img placeholder-grande">{{ p.nombre.charAt(0) }}</div>
                }
              </div>

              <div class="detalle-info">
                <span class="card-categoria">{{ p.categoria_nombre || 'Sin categoria' }}</span>
                <h2 class="detalle-nombre">{{ p.nombre }}</h2>
                <p class="detalle-vendedor">Vendido por <strong>{{ p.empresa_nombre }}</strong></p>

                @if (p.total_comentarios > 0) {
                  <p class="detalle-calificacion">
                    ★ {{ p.promedio_calificacion }} <span class="gris">({{ p.total_comentarios }} comentarios)</span>
                  </p>
                } @else {
                  <p class="detalle-calificacion gris">Sin comentarios todavia</p>
                }

                <p class="detalle-precio">\${{ p.precio | number }}</p>
                <p class="detalle-descripcion">{{ p.descripcion || 'Sin descripcion.' }}</p>

                @if (p.stock > 0) {
                  <button type="button" class="btn btn-primario"
                          [disabled]="agregandoId() === p.id"
                          (click)="agregarAlCarrito(p)">
                    @if (agregandoId() === p.id) { Agregando... } @else { + Agregar al carrito }
                  </button>
                } @else {
                  <span class="sin-stock">Sin stock</span>
                }
              </div>
            </div>

            <div class="comentarios">
              <h3>Comentarios</h3>

              @if (sesion()) {
                <div class="form-comentario">
                  <label>Tu calificacion</label>
                  <div class="estrellas">
                    @for (n of [1, 2, 3, 4, 5]; track n) {
                      <button type="button" class="estrella" [class.estrella-activa]="n <= miCalificacion()"
                              (click)="miCalificacion.set(n)">★</button>
                    }
                  </div>
                  <textarea class="input" rows="2" placeholder="Que te parecio el producto? (opcional)"
                            [(ngModel)]="miComentario"></textarea>
                  @if (errorComentario()) {
                    <p class="error-comentario">{{ errorComentario() }}</p>
                  }
                  <button type="button" class="btn btn-secundario btn-sm" [disabled]="enviandoComentario()"
                          (click)="enviarComentario(p.id)">
                    @if (enviandoComentario()) { Enviando... } @else { Publicar comentario }
                  </button>
                </div>
              } @else {
                <p class="gris"><a routerLink="/login">Inicia sesion</a> para dejar tu comentario.</p>
              }

              @if (cargandoComentarios()) {
                <p class="gris">Cargando comentarios...</p>
              } @else if (!comentarios().length) {
                <p class="gris">Aun no hay comentarios para este producto.</p>
              } @else {
                <ul class="lista-comentarios">
                  @for (c of comentarios(); track c.id) {
                    <li>
                      <div class="comentario-cabeza">
                        <strong>{{ c.usuario_nombre || 'Comprador' }}</strong>
                        <span class="comentario-estrellas">{{ estrellasTexto(c.calificacion) }}</span>
                        <span class="gris">{{ c.created_at | date: 'dd/MM/yyyy' }}</span>
                      </div>
                      @if (c.comentario) {
                        <p>{{ c.comentario }}</p>
                      }
                    </li>
                  }
                </ul>
              }
            </div>
          </div>
        </div>
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
      display: inline-flex; align-items: center; gap: 8px;
      padding: 8px 18px; background: var(--primario); color: #fff;
      border: 0; border-radius: 8px; font: inherit; font-size: 14px;
      font-weight: 600; text-decoration: none; cursor: pointer; white-space: nowrap;
      transition: opacity .15s, transform .15s;
    }
    .btn-carrito:hover { opacity: .9; transform: translateY(-1px); }
    .btn-carrito-icono { width: 18px; height: 18px; flex-shrink: 0; }
    .btn-carrito-contador {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 20px; height: 20px; padding: 0 5px; border-radius: 999px;
      background: rgba(255,255,255,.25); font-size: 12px; font-weight: 700;
    }
    .btn-carrito-contador.rebote { animation: rebote-contador .5s cubic-bezier(.36,1.8,.4,1); }
    @keyframes rebote-contador {
      0%, 100% { transform: scale(1); }
      30% { transform: scale(1.5); }
      55% { transform: scale(.9); }
      75% { transform: scale(1.15); }
    }

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
      cursor: pointer; transition: all .2s ease;
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
    @media (min-width: 980px) {
      .grid { grid-template-columns: repeat(4, 1fr); }
    }
    .card {
      background: #fff; border: 1px solid var(--linea); border-radius: 12px;
      overflow: hidden;
    }
    .tarjeta-hover { transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease; }
    .tarjeta-hover:hover {
      transform: translateY(-6px); border-color: transparent;
      box-shadow: 0 16px 32px rgba(15,23,42,.12), 0 4px 10px rgba(15,23,42,.06);
    }
    .card-img {
      position: relative; height: 180px; background: #f1f5f9; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
    }
    .card-img img { width: 100%; height: 100%; object-fit: cover; transition: transform .35s ease; }
    .tarjeta-hover:hover .card-img img { transform: scale(1.08); }
    .placeholder-img {
      width: 60px; height: 60px; border-radius: 50%;
      background: var(--primario); color: #fff; font-size: 24px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
    }
    .card-badges {
      position: absolute; top: 8px; left: 8px; right: 8px;
      display: flex; flex-direction: column; align-items: flex-start; gap: 6px;
    }
    .badge {
      padding: 4px 9px; border-radius: 999px; box-shadow: 0 2px 6px rgba(0,0,0,.08);
      font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em;
    }
    .badge-urgencia { background: #fef3f2; color: #b42318; border: 1px solid #fecdca; }
    .badge-top { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
    .badge-nuevo { background: var(--primario-suave); color: var(--primario-osc); border: 1px solid #bfdbfe; }
    .card-body { padding: 14px; }
    .card-categoria { font-size: 12px; color: var(--primario); font-weight: 600; text-transform: uppercase; }
    .card-nombre { margin: 6px 0 4px; font-size: 16px; }
    .card-calificacion { margin: 0 0 6px; font-size: 12.5px; font-weight: 600; color: #b45309; }
    .estrellas-mini { color: #f59e0b; letter-spacing: 1px; }
    .card-sku { margin: 0 0 12px; font-size: 12px; color: var(--gris); }
    .card-footer { display: flex; justify-content: space-between; align-items: center; }
    .card-precio { font-size: 18px; font-weight: 700; color: var(--primario); }
    .btn-agregar {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 6px 14px; background: var(--primario); color: #fff;
      border: 0; border-radius: 6px; font: inherit; font-size: 13px;
      font-weight: 600; cursor: pointer; transition: opacity .15s, transform .1s, background .2s;
    }
    .icono-carrito, .icono-check { width: 15px; height: 15px; flex-shrink: 0; }
    .btn-agregar:hover { opacity: .9; transform: translateY(-1px); }
    .btn-agregar:active { transform: scale(.94); }
    .btn-agregar:disabled { opacity: .5; cursor: not-allowed; }
    .btn-agregar-ok { background: #067647; animation: pulso-ok .35s ease; }
    @keyframes pulso-ok {
      0% { transform: scale(1); } 50% { transform: scale(1.06); } 100% { transform: scale(1); }
    }
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

    /* Modal de detalle de producto (doble click en la tarjeta) */
    .modal-fondo {
      position: fixed; inset: 0; z-index: 1000; background: rgba(15, 23, 42, .55);
      display: flex; align-items: flex-start; justify-content: center;
      padding: var(--e5) var(--e4); overflow-y: auto;
    }
    .modal-caja {
      position: relative; background: #fff; border-radius: 14px; max-width: 760px;
      width: 100%; padding: var(--e5); margin-top: var(--e5);
      box-shadow: 0 24px 60px rgba(0,0,0,.25);
    }
    .modal-cerrar {
      position: absolute; top: 14px; right: 14px; width: 32px; height: 32px;
      border-radius: 50%; border: 1px solid var(--linea); background: #fff;
      cursor: pointer; font-size: 14px; color: var(--gris);
    }
    .modal-cerrar:hover { color: var(--tinta); border-color: var(--gris); }

    .detalle { display: grid; grid-template-columns: 1fr 1fr; gap: var(--e5); }
    .detalle-img {
      height: 280px; background: #f1f5f9; border-radius: 10px; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
    }
    .detalle-img img { max-width: 100%; max-height: 100%; object-fit: contain; }
    .placeholder-grande { width: 100px; height: 100px; font-size: 36px; }
    .detalle-info { display: flex; flex-direction: column; gap: 6px; }
    .detalle-nombre { margin: 0; font-size: 22px; }
    .detalle-vendedor { margin: 0; font-size: 14px; color: var(--gris); }
    .detalle-calificacion { margin: 0; font-size: 14px; color: #b45309; font-weight: 600; }
    .detalle-precio { margin: 6px 0; font-size: 24px; font-weight: 700; color: var(--primario); }
    .detalle-descripcion { margin: 0 0 var(--e3); font-size: 14px; color: var(--tinta); line-height: 1.5; }
    .gris { color: var(--gris); }

    .comentarios { margin-top: var(--e5); padding-top: var(--e5); border-top: 1px solid var(--linea); }
    .comentarios h3 { margin: 0 0 var(--e3); font-size: 16px; }
    .form-comentario {
      display: flex; flex-direction: column; gap: 8px; margin-bottom: var(--e4);
      padding: var(--e3); background: #f8fafc; border-radius: 10px;
    }
    .estrellas { display: flex; gap: 4px; }
    .estrella { border: 0; background: none; font-size: 20px; color: #d1d5db; cursor: pointer; padding: 0; }
    .estrella-activa { color: #f59e0b; }
    .error-comentario { margin: 0; color: #b42318; font-size: 13px; }
    .lista-comentarios { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--e3); }
    .lista-comentarios li { padding-bottom: var(--e3); border-bottom: 1px solid var(--linea); }
    .lista-comentarios li:last-child { border-bottom: 0; padding-bottom: 0; }
    .comentario-cabeza { display: flex; align-items: center; gap: 10px; font-size: 13.5px; margin-bottom: 4px; }
    .comentario-estrellas { color: #f59e0b; }
    .lista-comentarios p { margin: 0; font-size: 14px; color: var(--tinta); }

    @media (max-width: 640px) {
      .detalle { grid-template-columns: 1fr; }
      .detalle-img { height: 200px; }
    }

    @media (prefers-reduced-motion: reduce) {
      .card-img img, .btn-agregar, .chip, .tarjeta-hover { transition: none; }
      .tarjeta-hover:hover, .tarjeta-hover:hover .card-img img { transform: none; }
      .skeleton::after { animation: none; }
      .exito-toast { animation: none; }
      .btn-agregar-ok, .btn-carrito-contador.rebote { animation: none; }
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
  readonly carritoAnimado = signal(false);
  /** IDs de producto cuya imagen fallo al cargar; se muestra el placeholder. */
  readonly imagenesFallidas = signal<Set<string>>(new Set());

  busqueda = '';
  categoriaSeleccionada = '';
  orden = 'nombre';

  readonly totalItems = signal(0);
  readonly pagina = signal(1);
  readonly totalPaginas = signal(1);

  // ---- Detalle de producto (modal por doble click) ----
  readonly productoDetalle = signal<ProductoTienda | null>(null);
  readonly comentarios = signal<ComentarioProducto[]>([]);
  readonly cargandoComentarios = signal(false);
  readonly miCalificacion = signal(5);
  miComentario = '';
  readonly enviandoComentario = signal(false);
  readonly errorComentario = signal('');
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
        this.carritoAnimado.set(false);
        requestAnimationFrame(() => this.carritoAnimado.set(true));
        setTimeout(() => this.carritoAnimado.set(false), 600);
      },
      error: (e) => { this.error.set(e.detalle || 'Error al agregar.'); this.agregandoId.set(null); },
    });
  }

  salir(): void {
    this.auth.cerrarSesion();
  }

  // ---- Detalle de producto ----
  abrirDetalle(producto: ProductoTienda): void {
    this.productoDetalle.set(producto);
    this.miCalificacion.set(5);
    this.miComentario = '';
    this.errorComentario.set('');
    this.cargarComentarios(producto.id);
  }

  cerrarDetalle(): void {
    this.productoDetalle.set(null);
    this.comentarios.set([]);
  }

  cargarComentarios(productoId: string): void {
    this.cargandoComentarios.set(true);
    this.tienda.listarComentarios(productoId).subscribe({
      next: (r) => { this.comentarios.set(r.resultados); this.cargandoComentarios.set(false); },
      error: () => this.cargandoComentarios.set(false),
    });
  }

  enviarComentario(productoId: string): void {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/login']);
      return;
    }
    this.enviandoComentario.set(true);
    this.errorComentario.set('');
    this.tienda.comentarProducto(productoId, {
      calificacion: this.miCalificacion(),
      comentario: this.miComentario.trim(),
    }).subscribe({
      next: () => {
        this.miComentario = '';
        this.enviandoComentario.set(false);
        this.cargarComentarios(productoId);
      },
      error: (e) => {
        this.errorComentario.set(e.detalle || 'No se pudo publicar el comentario.');
        this.enviandoComentario.set(false);
      },
    });
  }

  /** Estrellas llenas/vacias en texto para mostrar la calificacion de otros. */
  estrellasTexto(calificacion: number): string {
    return '★'.repeat(calificacion) + '☆'.repeat(5 - calificacion);
  }

  redondear(valor: number | null): number {
    return valor ? Math.round(valor) : 0;
  }

  /** Deja de intentar cargar la imagen rota; el template cae al placeholder. */
  marcarImagenFallida(productoId: string): void {
    this.imagenesFallidas.update((set) => new Set(set).add(productoId));
  }

  esTopCalificado(p: ProductoTienda): boolean {
    return (p.promedio_calificacion ?? 0) >= 4.5 && p.total_comentarios >= 3;
  }

  /** Publicado en los ultimos 14 dias. */
  esNuevo(p: ProductoTienda): boolean {
    const dias = (Date.now() - new Date(p.created_at).getTime()) / 86_400_000;
    return dias <= 14;
  }
}
