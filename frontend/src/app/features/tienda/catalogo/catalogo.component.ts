import { DatePipe, DecimalPipe } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  inject,
  signal,
  computed,
  OnInit,
  OnDestroy,
  viewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import { AuthService } from '../../../core/services/auth.service';
import {
  ProductoTienda,
  CategoriaTienda,
  ComentarioProducto,
  Favorito,
} from '../../../core/models/tienda.model';
import { BrilloCursorDirective } from '../../../shared/directives/brillo-cursor.directive';
import { RevelarAlEntrarDirective } from '../../../shared/directives/revelar-al-entrar.directive';
import { programarAviso } from '../../../core/utils/temporizador.util';

@Component({
  selector: 'app-catalogo',
  imports: [
    DatePipe,
    DecimalPipe,
    FormsModule,
    RouterLink,
    BrilloCursorDirective,
    RevelarAlEntrarDirective,
  ],
  templateUrl: './catalogo.component.html',
  styleUrl: './catalogo.component.css',
})
export class CatalogoComponent implements OnInit, OnDestroy {
  private readonly tienda = inject(TiendaService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly sesion = this.auth.usuario;
  readonly esAdministrador = this.auth.esAdministrador;

  readonly productos = signal<ProductoTienda[]>([]);
  readonly categorias = signal<CategoriaTienda[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly agregandoId = signal<string | null>(null);
  readonly agregadoId = signal<string | null>(null);
  readonly exito = signal('');
  readonly carritoAnimado = signal(false);
  /** Menu de opciones (hamburguesa) del encabezado. */
  readonly menuAbierto = signal(false);
  /** IDs de producto cuya imagen fallo al cargar; se muestra el placeholder. */
  readonly imagenesFallidas = signal<Set<string>>(new Set());
  /** Onda expansiva al hacer doble click en una tarjeta (id de producto activo + punto de origen en %). */
  readonly tarjetaEfecto = signal<string | null>(null);
  readonly ondaPos = signal<{ x: number; y: number }>({ x: 50, y: 50 });

  // ---- Favoritos ----
  /** Producto al que se le esta aplicando/quitando el corazon ahora mismo. */
  readonly favoritoCambioId = signal<string | null>(null);
  /** IDs marcados como favorito por el usuario (mapa id -> true). */
  readonly favoritosMap = signal<Set<string>>(new Set());

  // ---- Cantidad elegida en el modal de detalle ----
  readonly cantidad = signal(1);

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

  // ---- Carousel de productos destacados en el hero ----
  readonly heroSlides = signal<ProductoTienda[]>([]);
  readonly heroIndex = signal(0);
  readonly heroPausado = signal(false);
  private heroTimer: ReturnType<typeof setInterval> | null = null;

  // ---- Sugerencias del buscador (autocompletado) ----
  readonly sugerencias = signal<ProductoTienda[]>([]);
  readonly mostrarSugerencias = signal(false);
  readonly cargandoSugerencias = signal(false);
  private sugerenciasTimer: ReturnType<typeof setTimeout> | null = null;

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
    this.cargarFavoritos();
    this.cargarDestacados();
    this.heroTimer = setInterval(() => {
      if (this.heroPausado() || this.heroSlides().length < 2) return;
      this.heroSiguiente();
    }, 5000);
  }

  ngOnDestroy(): void {
    if (this.heroTimer) clearInterval(this.heroTimer);
    if (this.busquedaTimer) clearTimeout(this.busquedaTimer);
    if (this.sugerenciasTimer) clearTimeout(this.sugerenciasTimer);
  }

  /** Banner del hero: productos con imagen mejor calificados (o mas recientes si nadie ha calificado aun). */
  cargarDestacados(): void {
    this.tienda.listarCatalogo({ orden: 'reciente' }).subscribe({
      next: (r) => {
        const conImagen = r.resultados.filter((p) => !!p.imagen);
        const ordenados = [...conImagen].sort(
          (a, b) =>
            (b.promedio_calificacion ?? 0) - (a.promedio_calificacion ?? 0) ||
            b.total_comentarios - a.total_comentarios,
        );
        this.heroSlides.set(ordenados.slice(0, 5));
      },
      error: () => {},
    });
  }

  heroSiguiente(): void {
    const total = this.heroSlides().length;
    if (!total) return;
    this.heroIndex.set((this.heroIndex() + 1) % total);
  }

  heroAnterior(): void {
    const total = this.heroSlides().length;
    if (!total) return;
    this.heroIndex.set((this.heroIndex() - 1 + total) % total);
  }

  irHeroSlide(i: number): void {
    this.heroIndex.set(i);
  }

  cargarCatalogo(): void {
    this.cargando.set(true);
    this.tienda
      .listarCatalogo({
        busqueda: this.busqueda,
        categoria: this.categoriaSeleccionada,
        orden: this.orden,
        pagina: String(this.pagina()),
      })
      .subscribe({
        next: (r) => {
          this.productos.set(r.resultados);
          this.categorias.set(r.categorias || []);
          this.totalPaginas.set(r.total_paginas || 1);
          this.cargando.set(false);
        },
        error: (e) => {
          this.error.set(e.detalle || 'Error al cargar.');
          this.cargando.set(false);
        },
      });
  }

  /** Busqueda/filtro nuevo: siempre vuelve a la pagina 1. */
  buscar(): void {
    this.mostrarSugerencias.set(false);
    this.pagina.set(1);
    this.cargarCatalogo();
  }

  /** Debounce de 350ms para la busqueda completa y de 250ms para las sugerencias. */
  onBusquedaInput(): void {
    if (this.busquedaTimer) clearTimeout(this.busquedaTimer);
    this.busquedaTimer = setTimeout(() => this.buscar(), 350);

    const texto = this.busqueda.trim();
    if (this.sugerenciasTimer) clearTimeout(this.sugerenciasTimer);
    if (texto.length < 2) {
      this.mostrarSugerencias.set(false);
      this.sugerencias.set([]);
      return;
    }
    this.sugerenciasTimer = setTimeout(() => this.cargarSugerencias(texto), 250);
  }

  onBuscadorFocus(): void {
    if (this.busqueda.trim().length >= 2 && this.sugerencias().length) {
      this.mostrarSugerencias.set(true);
    }
  }

  /** Cierra el menu de sugerencias solo si el foco sale del contenedor por completo. */
  onBuscadorBlur(evento: FocusEvent): void {
    const contenedor = evento.currentTarget as HTMLElement;
    const siguiente = evento.relatedTarget as Node | null;
    if (!siguiente || !contenedor.contains(siguiente)) {
      this.mostrarSugerencias.set(false);
    }
  }

  cargarSugerencias(texto: string): void {
    this.cargandoSugerencias.set(true);
    this.mostrarSugerencias.set(true);
    this.tienda.listarCatalogo({ busqueda: texto }).subscribe({
      next: (r) => {
        if (this.busqueda.trim() !== texto) return; // respuesta obsoleta, ya se escribio otra cosa
        this.sugerencias.set(r.resultados.slice(0, 6));
        this.cargandoSugerencias.set(false);
      },
      error: () => {
        this.cargandoSugerencias.set(false);
        this.sugerencias.set([]);
      },
    });
  }

  seleccionarSugerencia(producto: ProductoTienda): void {
    this.mostrarSugerencias.set(false);
    this.busqueda = producto.nombre;
    this.abrirDetalle(producto);
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
        programarAviso(this.destroyRef, () => this.agregadoId.set(null), 1200);
        this.exito.set(`${producto.nombre} agregado al carrito`);
        programarAviso(this.destroyRef, () => this.exito.set(''), 3000);
        this.carritoAnimado.set(false);
        requestAnimationFrame(() => this.carritoAnimado.set(true));
        programarAviso(this.destroyRef, () => this.carritoAnimado.set(false), 600);
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al agregar.');
        this.agregandoId.set(null);
      },
    });
  }

  /** Añade la cantidad elegida en el modal (por defecto 1). */
  agregarAlCarritoModal(producto: ProductoTienda): void {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/login'], { queryParams: { redirigir: '/' } });
      return;
    }
    this.agregarAlCarritoConCantidad(producto, this.cantidad());
  }

  /** Suma una cantidad y, si hace falta, abre el checkout. Devuelve el carrito. */
  private agregarAlCarritoConCantidad(producto: ProductoTienda, cantidad: number): void {
    this.agregandoId.set(producto.id);
    this.error.set('');
    this.tienda.agregarItem(producto.id, cantidad).subscribe({
      next: (c) => {
        this.totalItems.set(c.total_items);
        this.agregandoId.set(null);
        this.agregadoId.set(producto.id);
        programarAviso(this.destroyRef, () => this.agregadoId.set(null), 1200);
      },
      error: (e) => {
        this.error.set(e.detalle || 'Error al agregar.');
        this.agregandoId.set(null);
      },
    });
  }

  /** 'Comprar ahora': agrega la cantidad elegida al carrito y salta al checkout. */
  comprarProducto(producto: ProductoTienda): void {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/login'], { queryParams: { redirigir: '/checkout' } });
      return;
    }
    this.agregarAlCarritoConCantidad(producto, this.cantidad());
    this.router.navigate(['/checkout']);
  }

  /** Carga los favoritos del usuario autenticado para pintar los corazones. */
  cargarFavoritos(): void {
    if (!this.auth.estaAutenticado()) return;
    this.tienda.listarFavoritos().subscribe({
      next: (favoritos) => this.favoritosMap.set(new Set(favoritos.map((f) => f.producto))),
      error: () => {},
    });
  }

  esFavorito(productoId: string): boolean {
    return this.favoritosMap().has(productoId);
  }

  /** Corazon: alterna el favorito. Sin sesion, invita a iniciar sesion. */
  alternarFavorito(producto: ProductoTienda): void {
    if (!this.auth.estaAutenticado()) {
      this.preguntarLogin();
      return;
    }
    const id = producto.id;
    const activando = !this.esFavorito(id);
    this.favoritoCambioId.set(id);

    const alTerminar = () => {
      this.favoritosMap.update((set) => {
        const nuevo = new Set(set);
        activando ? nuevo.add(id) : nuevo.delete(id);
        return nuevo;
      });
      this.favoritoCambioId.set(null);
      this.exito.set(
        activando
          ? `${producto.nombre} guardado en favoritos`
          : `${producto.nombre} eliminado de favoritos`,
      );
      programarAviso(this.destroyRef, () => this.exito.set(''), 2500);
    };

    if (activando) {
      this.tienda.agregarFavorito(id).subscribe({
        next: alTerminar,
        error: () => this.favoritoCambioId.set(null),
      });
    } else {
      this.tienda.quitarFavorito(id).subscribe({
        next: alTerminar,
        error: () => this.favoritoCambioId.set(null),
      });
    }
  }

  /** Sin sesion: pregunta si quiere ir al login antes de guardar el favorito. */
  private preguntarLogin(): void {
    const ir = window.confirm('Para guardar favoritos debes iniciar sesion. ¿Quieres ir al login?');
    if (ir) this.router.navigate(['/login']);
  }

  /** Valida la cantidad tecleada (1..stock) antes de guardarla. */
  setCantidad(valor: number): void {
    const detalle = this.productoDetalle();
    const max = detalle?.stock ?? Number.MAX_SAFE_INTEGER;
    const normalizado = Math.min(Math.max(Math.floor(valor) || 1, 1), max);
    this.cantidad.set(normalizado);
  }

  salir(): void {
    this.auth.cerrarSesion();
  }

  // ---- Detalle de producto ----
  /** Si viene de un doble click en la tarjeta, dispara la onda expansiva
   * desde el punto exacto del clic y abre el modal justo despues. */
  abrirDetalle(producto: ProductoTienda, evento?: MouseEvent): void {
    if (evento) {
      const tarjeta = (evento.currentTarget as HTMLElement).getBoundingClientRect();
      this.ondaPos.set({
        x: ((evento.clientX - tarjeta.left) / tarjeta.width) * 100,
        y: ((evento.clientY - tarjeta.top) / tarjeta.height) * 100,
      });
      this.tarjetaEfecto.set(producto.id);
      programarAviso(this.destroyRef, () => this.tarjetaEfecto.set(null), 550);
      setTimeout(() => this.mostrarDetalle(producto), 180);
      return;
    }
    this.mostrarDetalle(producto);
  }

  private mostrarDetalle(producto: ProductoTienda): void {
    this.productoDetalle.set(producto);
    this.cantidad.set(1);
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
      next: (r) => {
        this.comentarios.set(r.resultados);
        this.cargandoComentarios.set(false);
      },
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
    this.tienda
      .comentarProducto(productoId, {
        calificacion: this.miCalificacion(),
        comentario: this.miComentario.trim(),
      })
      .subscribe({
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
