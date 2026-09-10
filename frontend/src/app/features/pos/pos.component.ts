/**
 * POS — punto de venta en mostrador (Flujo 2)
 *
 * Que hace: arma una venta buscando productos, controla stock, aplica el
 * cliente (o el generico de mostrador) y registra la venta.
 * Ruta: /pos (authGuard + personalGuard).
 * Por que asi: el total se calcula en el frontend solo para mostrarlo; el que
 * vale es el que devuelve el backend al crear la venta. Si el stock cambio
 * mientras se armaba el carrito, el backend responde con el detalle de que
 * falta y la pantalla lo muestra producto por producto.
 */

import { DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CatalogoService } from '../../core/services/catalogo.service';
import {
  Cliente,
  Producto,
  LineaPOS,
  VentaPOSInput,
  StockInsuficiente,
} from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { debounce } from '../../core/utils/temporizador.util';

@Component({
  selector: 'app-pos',
  imports: [DecimalPipe, FormsModule, RouterLink, PanelShellComponent],
  templateUrl: './pos.component.html',
  styleUrls: ['./pos.component.css'],
})
export class PosComponent {
  private readonly catalogo = inject(CatalogoService);
  private readonly destroyRef = inject(DestroyRef);
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  private readonly buscarProductosDebounced = debounce(
    this.destroyRef,
    () => this.buscarProductosInmediato(),
    300,
  );

  readonly clientes = signal<Cliente[]>([]);
  readonly cargandoClientes = signal(true);
  readonly errorClientes = signal('');
  /** Id del cliente "Consumidor final": se preselecciona para venta rapida
   * de mostrador (RN: fila, tienda fisica), sin bloquear elegir uno real. */
  readonly clienteGenericoId = signal<string | null>(null);
  busquedaProducto = '';
  readonly resultadosBusqueda = signal<Producto[]>([]);
  readonly lineas = signal<LineaPOS[]>([]);
  descuento = 0;
  notas = '';
  readonly metodoPago = signal('efectivo');
  readonly cargando = signal(false);
  readonly error = signal('');
  readonly erroresStock = signal<StockInsuficiente[]>([]);
  readonly ventaCreada = signal<any>(null);

  readonly metodosPago = [
    { valor: 'efectivo', etiqueta: 'Efectivo' },
    { valor: 'transferencia', etiqueta: 'Transferencia' },
    { valor: 'nequi', etiqueta: 'Nequi' },
    { valor: 'daviplata', etiqueta: 'Daviplata' },
    { valor: 'tarjeta', etiqueta: 'Tarjeta' },
  ];

  readonly subtotal = computed(() => this.lineas().reduce((sum, l) => sum + l.subtotal, 0));
  readonly total = computed(() => Math.max(this.subtotal() - this.descuento, 0));
  readonly puedeConfirmar = computed(() => this.lineas().length > 0 && !!this.clienteSeleccionado);

  clienteSeleccionado = '';

  constructor() {
    this.cargarClientes();
    this.cargarClienteGenerico();
  }

  cargarClientes(): void {
    this.cargandoClientes.set(true);
    this.catalogo.listarClientes().subscribe({
      next: (r) => {
        this.clientes.set(r.resultados);
        this.errorClientes.set('');
        this.cargandoClientes.set(false);
      },
      error: (e) => {
        this.errorClientes.set(e.detalle ?? 'No se pudieron cargar los clientes.');
        this.cargandoClientes.set(false);
      },
    });
  }

  /** Trae (o crea) el cliente generico y lo deja preseleccionado, sin
   * esperar a que cargarClientes() termine ni pisar una eleccion previa. */
  cargarClienteGenerico(): void {
    this.catalogo.obtenerClienteGenerico().subscribe({
      next: (c) => {
        this.clienteGenericoId.set(c.id);
        if (!this.clientes().some((x) => x.id === c.id)) {
          this.clientes.update((lista) => [c, ...lista]);
        }
        if (!this.clienteSeleccionado) this.clienteSeleccionado = c.id;
      },
      error: () => {},
    });
  }

  buscarProductos(): void {
    if (this.busquedaProducto.length < 2) {
      this.resultadosBusqueda.set([]);
      return;
    }
    this.buscarProductosDebounced();
  }

  private buscarProductosInmediato(): void {
    this.catalogo.listarProductos({ busqueda: this.busquedaProducto, activo: true }).subscribe({
      next: (r) => this.resultadosBusqueda.set(r.resultados),
      error: () => this.resultadosBusqueda.set([]),
    });
  }

  agregarProducto(producto: Producto): void {
    const existente = this.lineas().find((l) => l.producto === producto.id);
    if (existente) {
      existente.cantidad += 1;
      existente.subtotal = existente.cantidad * existente.precio_unitario;
      this.lineas.update((l) => [...l]);
    } else {
      this.lineas.update((l) => [
        ...l,
        {
          producto: producto.id,
          nombre: producto.nombre,
          sku: producto.sku,
          precio_unitario: Number(producto.precio),
          cantidad: 1,
          stock_disponible: producto.stock,
          subtotal: Number(producto.precio),
        },
      ]);
    }
    this.resultadosBusqueda.set([]);
    this.busquedaProducto = '';
  }

  eliminarLinea(linea: LineaPOS): void {
    this.lineas.update((l) => l.filter((x) => x.producto !== linea.producto));
  }

  recalcular(): void {
    this.lineas.update((l) =>
      l.map((linea) => ({
        ...linea,
        cantidad: Math.max(1, Math.min(linea.cantidad, linea.stock_disponible)),
        subtotal:
          Math.max(1, Math.min(linea.cantidad, linea.stock_disponible)) * linea.precio_unitario,
      })),
    );
  }

  confirmarVenta(): void {
    if (!this.clienteSeleccionado || !this.lineas().length) return;

    this.cargando.set(true);
    this.error.set('');
    this.erroresStock.set([]);

    const input: VentaPOSInput = {
      cliente: this.clienteSeleccionado,
      metodo_pago: this.metodoPago(),
      descuento: this.descuento,
      notas: this.notas,
      detalles: this.lineas().map((l) => ({
        producto: l.producto,
        cantidad: l.cantidad,
      })),
    };

    this.catalogo.crearVentaPOS(input).subscribe({
      next: (venta) => {
        this.ventaCreada.set(venta);
        this.cargando.set(false);
      },
      error: (e) => {
        if (e.codigo === 'STOCK_INSUFICIENTE') {
          this.erroresStock.set(e.productos || []);
        } else {
          this.error.set(e.detalle || 'Error al crear la venta.');
        }
        this.cargando.set(false);
      },
    });
  }

  nuevaVenta(): void {
    this.lineas.set([]);
    this.descuento = 0;
    this.notas = '';
    this.clienteSeleccionado = '';
    this.ventaCreada.set(null);
    this.error.set('');
    this.erroresStock.set([]);
  }
}
