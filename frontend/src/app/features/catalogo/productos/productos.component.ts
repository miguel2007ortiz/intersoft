/**
 * Productos — catalogo interno de la empresa (Flujo 2)
 *
 * Que hace: crea y edita productos con precio, stock, minimo, categoria e
 * imagen; permite desactivarlos.
 * Ruta: /productos (authGuard + personalGuard).
 * Por que asi: la imagen se sube como multipart al mismo endpoint; el stock
 * NO se edita a mano desde aqui, se mueve por ventas y por movimientos de
 * inventario, para que la trazabilidad no se rompa.
 */

import { Component, DestroyRef, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { PanelShellComponent } from '../../../shared/layout/panel-shell/panel-shell.component';
import { EstadoVacioComponent } from '../../../shared/estado-vacio/estado-vacio.component';
import { PaginadorComponent } from '../../../shared/paginador/paginador.component';
import { CatalogoService } from '../../../core/services/catalogo.service';
import { debounce, programarAviso } from '../../../core/utils/temporizador.util';
import { Categoria, ErrorCatalogo, Producto } from '../../../core/models/catalogo.model';
import { ConfirmacionService } from '../../../core/services/confirmacion.service';

const CERRAR_AVISO_MS = 4000;

/** Imagen que se pinta cuando la del producto no carga. Es un SVG en linea
 * (data URI) a proposito: no anade una peticion mas ni un archivo que se
 * pueda perder al desplegar, que es justo el fallo del que protege. */
export const IMAGEN_RESPALDO =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">' +
      '<rect width="48" height="48" rx="6" fill="#e5e7eb"/>' +
      '<path d="M12 32l7-8 5 6 4-4 8 6z" fill="#9ca3af"/>' +
      '<circle cx="18" cy="17" r="3" fill="#9ca3af"/>' +
      '</svg>',
  );

@Component({
  selector: 'app-productos',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    PanelShellComponent,
    EstadoVacioComponent,
    PaginadorComponent,
  ],
  templateUrl: './productos.component.html',
  styleUrl: './productos.component.css',
})
export class ProductosComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly catalogo = inject(CatalogoService);
  private readonly destroyRef = inject(DestroyRef);

  readonly productos = signal<Producto[]>([]);
  readonly categorias = signal<Categoria[]>([]);
  readonly cargando = signal(true);
  readonly guardando = signal(false);
  /** Error al cargar el listado (estado-vacio + reintento, igual que
   * ventas/tienda). `error()` queda para errores de formulario/acciones. */
  readonly errorCarga = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);
  readonly editando = signal<Producto | null>(null);
  readonly formularioAbierto = signal(false);
  /** Archivo elegido en el input de imagen (null = sin cambio / sin imagen). */
  readonly imagenNueva = signal<File | null>(null);
  /** URL de la imagen actual (al editar) o del preview del archivo elegido. */
  readonly imagenPreview = signal<string | null>(null);
  readonly busqueda = signal('');
  /** filtro del catalogo: todos | activos | inactivos */
  readonly filtroEstado = signal<'todos' | 'activos' | 'inactivos'>('todos');
  /** Contadores del backend para el paginador (BUG-02). `total` son los
   * registros que cumplen el filtro, no los de la pagina. */
  readonly pagina = signal(1);
  readonly totalPaginas = signal(1);
  readonly total = signal(0);
  readonly desde = signal(0);
  readonly hasta = signal(0);
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  private readonly buscarDebounced = debounce(this.destroyRef, () => this.cargar(), 300);

  /** Motivo unico para el tooltip y para el lector de pantalla, para que no
   * puedan divergir. */
  readonly motivoNoEliminable =
    'No se puede eliminar: tiene ventas asociadas. Puedes desactivarlo.';

  readonly formulario = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(150)]],
    sku: ['', [Validators.required, Validators.maxLength(50)]],
    descripcion: ['', [Validators.maxLength(500)]],
    categoria_id: [''],
    precio: [0, [Validators.required, Validators.min(0)]],
    stock: [0, [Validators.required, Validators.min(0)]],
    stock_minimo: [10, [Validators.required, Validators.min(0)]],
  });

  ngOnInit(): void {
    this.cargar();
    this.cargarCategorias();
  }

  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set(null);
    const activo = this.filtroEstado() === 'todos' ? undefined : this.filtroEstado() === 'activos';
    // La busqueda y los filtros viajan siempre: cambiar de pagina no puede
    // perderlos (el paginador solo dice que pagina quiere).
    this.catalogo
      .listarProductos({ busqueda: this.busqueda(), activo, pagina: this.pagina() })
      .subscribe({
        next: (lista) => {
          this.productos.set(lista.resultados);
          this.total.set(lista.total ?? 0);
          this.pagina.set(lista.pagina ?? 1);
          this.totalPaginas.set(lista.total_paginas ?? 1);
          this.desde.set(lista.desde ?? 0);
          this.hasta.set(lista.hasta ?? 0);
          this.cargando.set(false);
        },
        error: (e) => {
          this.errorCarga.set(e.detalle ?? 'No se pudo cargar la lista.');
          this.cargando.set(false);
        },
      });
  }

  cargarCategorias(): void {
    this.catalogo.listarCategorias().subscribe(({ resultados }) => this.categorias.set(resultados));
  }

  buscar(evento: Event): void {
    this.busqueda.set((evento.target as HTMLInputElement).value.trim());
    // Un filtro nuevo cambia el conjunto: seguir en la pagina 7 dejaria la
    // tabla vacia sin explicacion.
    this.pagina.set(1);
    this.buscarDebounced();
  }

  filtrar(estado: 'todos' | 'activos' | 'inactivos'): void {
    this.filtroEstado.set(estado);
    this.pagina.set(1);
    this.cargar();
  }

  limpiarFiltros(): void {
    this.busqueda.set('');
    this.filtroEstado.set('todos');
    this.pagina.set(1);
    this.cargar();
  }

  irAPagina(numero: number): void {
    this.pagina.set(numero);
    this.cargar();
  }

  /** Imagen de respaldo si la URL del producto no carga (archivo borrado del
   * disco, permisos de media, etc.): sin esto queda el icono de rota. */
  imagenFallida(evento: Event): void {
    const img = evento.target as HTMLImageElement;
    if (img.src.endsWith(IMAGEN_RESPALDO)) return;
    img.src = IMAGEN_RESPALDO;
  }

  abrirCreacion(): void {
    this.editando.set(null);
    this.formulario.reset({
      nombre: '',
      sku: '',
      descripcion: '',
      categoria_id: '',
      precio: 0,
      stock: 0,
      stock_minimo: 10,
    });
    this.imagenNueva.set(null);
    this.imagenPreview.set(null);
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  abrirEdicion(producto: Producto): void {
    this.editando.set(producto);
    this.formulario.reset({
      nombre: producto.nombre,
      sku: producto.sku,
      descripcion: producto.descripcion,
      categoria_id: producto.categoria_id ?? '',
      precio: Number(producto.precio),
      stock: producto.stock,
      stock_minimo: producto.stock_minimo,
    });
    this.imagenNueva.set(null);
    this.imagenPreview.set(producto.imagen);
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  cerrarFormulario(): void {
    this.formularioAbierto.set(false);
    this.editando.set(null);
    this.imagenNueva.set(null);
    this.imagenPreview.set(null);
    this.error.set(null);
  }

  seleccionarImagen(evento: Event): void {
    const archivo = (evento.target as HTMLInputElement).files?.[0] ?? null;
    this.imagenNueva.set(archivo);
    this.imagenPreview.set(
      archivo ? URL.createObjectURL(archivo) : (this.editando()?.imagen ?? null),
    );
  }

  enviar(): void {
    if (this.guardando()) return;
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const valores = this.formulario.getRawValue();
    const datos = {
      ...valores,
      categoria_id: valores.categoria_id || null,
      ...(this.imagenNueva() ? { imagen: this.imagenNueva() } : {}),
    };
    const enEdicion = this.editando();
    this.guardando.set(true);

    const peticion = enEdicion
      ? this.catalogo.editarProducto(enEdicion.id, datos)
      : this.catalogo.crearProducto(datos);

    peticion.subscribe({
      next: () => {
        this.guardando.set(false);
        this.exito.set(enEdicion ? 'Producto actualizado.' : 'Producto creado.');
        this.cerrarFormulario();
        this.cargar();
        this.avisarExito();
      },
      error: (e: ErrorCatalogo) => {
        this.guardando.set(false);
        this.error.set(e.detalle ?? 'Datos invalidos.');
      },
    });
  }

  /** Oculta el aviso de "exito" despues de unos segundos. */
  private avisarExito(): void {
    programarAviso(this.destroyRef, () => this.exito.set(null), CERRAR_AVISO_MS);
  }

  alternarActivo(producto: Producto): void {
    const accion = producto.activo ? 'desactivar' : 'reactivar';
    this.catalogo.cambiarEstadoProducto(producto.id, accion).subscribe({
      next: (actualizado) => {
        this.productos.update((lista) =>
          lista.map((p) => (p.id === actualizado.id ? actualizado : p)),
        );
        this.exito.set(
          actualizado.activo ? 'Producto visible en el catalogo.' : 'Producto oculto del catalogo.',
        );
        this.avisarExito();
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'No se pudo cambiar el estado.'),
    });
  }

  async eliminar(producto: Producto): Promise<void> {
    const acepto = await this.confirmacion.pedir({
      titulo: 'Eliminar producto',
      mensaje:
        `Se eliminara "${producto.nombre}" del catalogo. Si ya tiene ventas ` +
        'registradas no se podra borrar, pero puedes desactivarlo.',
      confirmar: 'Eliminar producto',
      destructivo: true,
    });
    if (!acepto) return;
    this.catalogo.eliminarProducto(producto.id).subscribe({
      next: () => {
        this.exito.set('Producto eliminado.');
        this.cargar();
        this.avisarExito();
      },
      error: (e: ErrorCatalogo) => {
        // Regla fase 3: con ventas registradas solo se permite desactivar
        if (e.codigo === 'PRODUCTO_CON_VENTAS') {
          this.error.set(`${e.detalle} Usa "Desactivar" para ocultarlo.`);
          programarAviso(this.destroyRef, () => this.error.set(null), 6000);
          return;
        }
        this.error.set(e.detalle ?? 'No se pudo eliminar.');
      },
    });
  }

  campoInvalido(nombre: string): boolean {
    const control = this.formulario.get(nombre);
    return !!control && control.invalid && control.touched;
  }
}
