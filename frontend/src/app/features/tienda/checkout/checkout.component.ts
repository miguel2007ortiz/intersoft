import { DecimalPipe } from '@angular/common';
import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TiendaService } from '../../../core/services/tienda.service';
import {
  Carrito,
  CheckoutResponse,
  DatosComprador,
  StockInsuficiente,
} from '../../../core/models/tienda.model';
import { DEPARTAMENTOS_COLOMBIA } from '../../../shared/data/colombia-ubicaciones';

@Component({
  selector: 'app-checkout',
  imports: [DecimalPipe, FormsModule, RouterLink],
  templateUrl: './checkout.component.html',
  styleUrls: ['./checkout.component.css'],
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
  readonly mostrarFormComprador = signal(false);
  readonly guardandoComprador = signal(false);
  readonly errorComprador = signal('');
  datosComprador: DatosComprador = {
    tipo_documento: 'CC',
    numero_documento: '',
    telefono: '',
    direccion: '',
    ciudad: '',
  };
  readonly departamentos = DEPARTAMENTOS_COLOMBIA;
  departamentoSeleccionado = '';

  /** Ciudades del departamento elegido, para el select en cascada. */
  ciudadesDisponibles(): string[] {
    return (
      this.departamentos.find((d) => d.nombre === this.departamentoSeleccionado)?.ciudades ?? []
    );
  }

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
      next: (r) => {
        this.exito.set(r);
        this.cargando.set(false);
      },
      error: (e) => {
        if (e.codigo === 'SIN_CLIENTE') {
          this.mostrarFormComprador.set(true);
        } else if (e.codigo === 'STOCK_INSUFICIENTE') {
          this.erroresStock.set(e.productos || []);
        } else {
          this.error.set(e.detalle || 'Error al procesar el pago.');
        }
        this.cargando.set(false);
      },
    });
  }

  /** Vincula al usuario (sin importar su rol) con un Cliente del
   * marketplace y reintenta el pago automaticamente. */
  guardarDatosComprador(): void {
    this.guardandoComprador.set(true);
    this.errorComprador.set('');
    this.tienda.completarComprador(this.datosComprador).subscribe({
      next: () => {
        this.guardandoComprador.set(false);
        this.mostrarFormComprador.set(false);
        this.procesarPago();
      },
      error: (e) => {
        this.errorComprador.set(e.detalle || 'No se pudo guardar tus datos.');
        this.guardandoComprador.set(false);
      },
    });
  }
}
