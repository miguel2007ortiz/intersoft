import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PanelShellComponent } from '../../../shared/layout/panel-shell/panel-shell.component';
import { CatalogoService } from '../../../core/services/catalogo.service';
import {
  Categoria, ErrorCatalogo, Producto,
} from '../../../core/models/catalogo.model';

@Component({
  selector: 'app-productos',
  imports: [ReactiveFormsModule, RouterLink, PanelShellComponent],
  templateUrl: './productos.component.html',
  styleUrl: './productos.component.css',
})
export class ProductosComponent {
  private readonly fb = inject(FormBuilder);
  private readonly catalogo = inject(CatalogoService);

  readonly productos = signal<Producto[]>([]);
  readonly categorias = signal<Categoria[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);
  readonly editando = signal<Producto | null>(null);
  readonly formularioAbierto = signal(false);
  readonly busqueda = signal('');
  /** filtro del catalogo: todos | activos | inactivos */
  readonly filtroEstado = signal<'todos' | 'activos' | 'inactivos'>('todos');

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
    const activo = this.filtroEstado() === 'todos' ? undefined
      : this.filtroEstado() === 'activos';
    this.catalogo.listarProductos({ busqueda: this.busqueda(), activo }).subscribe({
      next: ({ resultados }) => {
        this.productos.set(resultados);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle ?? 'No se pudo cargar la lista.');
        this.cargando.set(false);
      },
    });
  }

  cargarCategorias(): void {
    this.catalogo.listarCategorias()
      .subscribe(({ resultados }) => this.categorias.set(resultados));
  }

  buscar(evento: Event): void {
    this.busqueda.set((evento.target as HTMLInputElement).value.trim());
    this.cargar();
  }

  filtrar(estado: 'todos' | 'activos' | 'inactivos'): void {
    this.filtroEstado.set(estado);
    this.cargar();
  }

  abrirCreacion(): void {
    this.editando.set(null);
    this.formulario.reset({
      nombre: '', sku: '', descripcion: '', categoria_id: '',
      precio: 0, stock: 0, stock_minimo: 10,
    });
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
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  cerrarFormulario(): void {
    this.formularioAbierto.set(false);
    this.editando.set(null);
    this.error.set(null);
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const valores = this.formulario.getRawValue();
    const datos = { ...valores, categoria_id: valores.categoria_id || null };
    const enEdicion = this.editando();

    const peticion = enEdicion
      ? this.catalogo.editarProducto(enEdicion.id, datos)
      : this.catalogo.crearProducto(datos);

    peticion.subscribe({
      next: () => {
        this.exito.set(enEdicion ? 'Producto actualizado.' : 'Producto creado.');
        this.cerrarFormulario();
        this.cargar();
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'Datos invalidos.'),
    });
  }

  alternarActivo(producto: Producto): void {
    const accion = producto.activo ? 'desactivar' : 'reactivar';
    this.catalogo.cambiarEstadoProducto(producto.id, accion).subscribe({
      next: (actualizado) => {
        this.productos.update((lista) =>
          lista.map((p) => (p.id === actualizado.id ? actualizado : p)));
        this.exito.set(actualizado.activo
          ? 'Producto visible en el catalogo.'
          : 'Producto oculto del catalogo.');
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'No se pudo cambiar el estado.'),
    });
  }

  eliminar(producto: Producto): void {
    if (!confirm(`¿Eliminar "${producto.nombre}"?`)) {
      return;
    }
    this.catalogo.eliminarProducto(producto.id).subscribe({
      next: () => {
        this.exito.set('Producto eliminado.');
        this.cargar();
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorCatalogo) => {
        // Regla fase 3: con ventas registradas solo se permite desactivar
        if (e.codigo === 'PRODUCTO_CON_VENTAS') {
          this.error.set(`${e.detalle} Usa "Desactivar" para ocultarlo.`);
          setTimeout(() => this.error.set(null), 6000);
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
