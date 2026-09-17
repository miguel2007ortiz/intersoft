/**
 * VentaDetalle — una venta con sus lineas y totales
 *
 * Que hace: encabezado (numero, fecha, cliente, vendedor, metodo de pago,
 * estado), tabla de lineas y totales. Boton Imprimir.
 * Ruta: /ventas/:id (authGuard + personalGuard).
 * Por que asi: los importes se pintan TAL CUAL vienen del API. El backend es
 * el dueno de los totales; recalcularlos aqui abriria la puerta a que la
 * pantalla y la factura digan cosas distintas por un redondeo.
 *
 * El backend responde 404 si la venta es de otra empresa, asi que esta
 * pantalla no necesita comprobar nada de aislamiento: solo distinguir "no
 * existe / no es tuya" de un fallo de red.
 */

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PanelShellComponent } from '../../../shared/layout/panel-shell/panel-shell.component';
import { EstadoVacioComponent } from '../../../shared/estado-vacio/estado-vacio.component';
import { CatalogoService } from '../../../core/services/catalogo.service';
import { ErrorCatalogo, Venta } from '../../../core/models/catalogo.model';

@Component({
  selector: 'app-venta-detalle',
  standalone: true,
  imports: [CommonModule, RouterLink, PanelShellComponent, EstadoVacioComponent],
  templateUrl: './venta-detalle.component.html',
  styleUrls: ['./venta-detalle.component.css'],
})
export class VentaDetalleComponent implements OnInit {
  private readonly ruta = inject(ActivatedRoute);
  private readonly catalogo = inject(CatalogoService);

  readonly venta = signal<Venta | null>(null);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  /** Distingue "no existe o no es de tu empresa" de un fallo de red, para
   * poder ofrecer reintentar solo cuando tiene sentido. */
  readonly noEncontrada = signal(false);

  readonly tieneLineas = computed(() => (this.venta()?.detalles?.length ?? 0) > 0);

  ngOnInit(): void {
    const id = this.ruta.snapshot.paramMap.get('id');
    if (!id) {
      this.noEncontrada.set(true);
      this.cargando.set(false);
      return;
    }
    this.cargar(id);
  }

  cargar(id: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.noEncontrada.set(false);
    this.catalogo.obtenerVenta(id).subscribe({
      next: (venta) => {
        this.venta.set(venta);
        this.cargando.set(false);
      },
      error: (e: ErrorCatalogo & { status?: number }) => {
        if (e.status === 404 || e.codigo === 'NO_ENCONTRADO') {
          this.noEncontrada.set(true);
        } else {
          this.error.set(e.detalle ?? 'No se pudo cargar la venta.');
        }
        this.cargando.set(false);
      },
    });
  }

  reintentar(): void {
    const id = this.ruta.snapshot.paramMap.get('id');
    if (id) this.cargar(id);
  }

  imprimir(): void {
    window.print();
  }
}
