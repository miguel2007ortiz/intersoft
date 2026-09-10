import { DatePipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  ENVIO_ESTADOS,
  ENVIO_TRANSICIONES,
  Envio,
  EnvioEstado,
} from '../../core/models/tienda.model';
import { DatosActualizarEnvio, EnviosService } from '../../core/services/envios.service';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { EstadoVacioComponent } from '../../shared/estado-vacio/estado-vacio.component';

/** Panel de despachos para el personal interno: cola de trabajo de envios
 * (mas antiguos primero), filtrable por estado, con gestion por pedido
 * (transportadora, guia, fecha estimada y avance de estado validado por el
 * backend: solo las transiciones de Envio.TRANSICIONES_VALIDAS). */
@Component({
  selector: 'app-envios',
  imports: [DatePipe, FormsModule, PanelShellComponent, EstadoVacioComponent],
  templateUrl: './envios.component.html',
  styleUrls: ['./envios.component.css'],
})
export class EnviosComponent implements OnInit {
  private readonly enviosService = inject(EnviosService);

  readonly envios = signal<Envio[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  filtroEstado: EnvioEstado | '' = '';

  readonly envioEditando = signal<Envio | null>(null);
  readonly estadosSiguientes = signal<EnvioEstado[]>([]);
  readonly nuevoEstado = signal<EnvioEstado | null>(null);
  readonly guardando = signal(false);
  readonly errorGuardado = signal('');

  transportadora = '';
  numeroGuia = '';
  fechaEstimada = '';
  notas = '';

  readonly ENVIO_ESTADOS = ENVIO_ESTADOS;

  etiquetaEstado(estado: EnvioEstado): string {
    return ENVIO_ESTADOS.find((e) => e.valor === estado)?.etiqueta ?? estado;
  }

  ngOnInit(): void {
    this.cargarEnvios();
  }

  cargarEnvios(): void {
    this.cargando.set(true);
    this.enviosService.listarEnvios(this.filtroEstado || undefined).subscribe({
      next: (r) => {
        this.envios.set(r.resultados);
        this.error.set(null);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle ?? 'No se pudo cargar la lista.');
        this.cargando.set(false);
      },
    });
  }

  gestionar(envio: Envio): void {
    this.envioEditando.set(envio);
    this.transportadora = envio.transportadora;
    this.numeroGuia = envio.numero_guia;
    this.fechaEstimada = envio.fecha_entrega_estimada ?? '';
    this.notas = envio.notas;
    this.estadosSiguientes.set(ENVIO_TRANSICIONES[envio.estado]);
    this.nuevoEstado.set(null);
    this.errorGuardado.set('');
  }

  elegirEstado(estado: EnvioEstado): void {
    this.nuevoEstado.set(this.nuevoEstado() === estado ? null : estado);
  }

  cancelar(): void {
    if (this.guardando()) return;
    this.envioEditando.set(null);
  }

  guardar(): void {
    const envio = this.envioEditando();
    if (!envio || this.guardando()) return;

    const datos: DatosActualizarEnvio = {
      transportadora: this.transportadora.trim(),
      numero_guia: this.numeroGuia.trim(),
      notas: this.notas.trim(),
      fecha_entrega_estimada: this.fechaEstimada || null,
    };
    const siguiente = this.nuevoEstado();
    if (siguiente) datos.estado = siguiente;

    this.guardando.set(true);
    this.errorGuardado.set('');
    this.enviosService.actualizarEnvio(envio.venta, datos).subscribe({
      next: () => {
        this.guardando.set(false);
        this.envioEditando.set(null);
        this.cargarEnvios();
      },
      error: (e) => {
        this.errorGuardado.set(e.detalle ?? 'No se pudo guardar el envio.');
        this.guardando.set(false);
      },
    });
  }
}
