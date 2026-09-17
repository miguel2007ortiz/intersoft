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
  /** Mensaje de la ultima accion sobre el recibo (envio o descarga). */
  readonly avisoRecibo = signal<string | null>(null);
  readonly reciboEnCurso = signal(false);

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

  /** Descarga el comprobante que el sistema emitio solo al completarse la
   * venta. Se pide al backend en vez de imprimir la pantalla: es el mismo
   * documento que recibio el comprador por correo. */
  descargarRecibo(): void {
    const venta = this.venta();
    if (!venta || this.reciboEnCurso()) return;
    this.reciboEnCurso.set(true);
    this.avisoRecibo.set(null);
    this.catalogo.descargarRecibo(venta.id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = `recibo-${venta.numero_factura}.html`;
        enlace.click();
        URL.revokeObjectURL(url);
      },
      error: (e: ErrorCatalogo) =>
        this.avisoRecibo.set(e.detalle ?? 'No se pudo descargar el recibo.'),
      complete: () => this.reciboEnCurso.set(false),
    });
  }

  /** Reenvia el recibo por correo. Util cuando el envio automatico fallo o el
   * cliente no tenia correo cuando se hizo la venta. */
  reenviarRecibo(): void {
    const venta = this.venta();
    if (!venta || this.reciboEnCurso()) return;
    this.reciboEnCurso.set(true);
    this.avisoRecibo.set(null);
    this.catalogo.reenviarRecibo(venta.id).subscribe({
      next: (r) => this.avisoRecibo.set(`Recibo ${r.numero} enviado a ${r.enviado_a}.`),
      error: (e: ErrorCatalogo) =>
        this.avisoRecibo.set(e.detalle ?? 'No se pudo reenviar el recibo.'),
      complete: () => this.reciboEnCurso.set(false),
    });
  }
}
