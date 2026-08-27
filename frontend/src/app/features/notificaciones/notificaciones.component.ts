import { Component, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MonitoreoService } from '../../core/services/monitoreo.service';
import { ErrorMonitoreo, Notificacion } from '../../core/models/monitoreo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

/** Fase 9: centro de notificaciones del ADMINISTRADOR.
 * Lista los avisos activos de la empresa y permite marcarlos como
 * revisados o resueltos (una notificacion resuelta sale del panel). */
@Component({
  selector: 'app-notificaciones',
  imports: [DatePipe, PanelShellComponent],
  templateUrl: './notificaciones.component.html',
  styleUrl: './notificaciones.component.css',
})
export class NotificacionesComponent implements OnInit {
  private readonly monitoreo = inject(MonitoreoService);

  readonly notificaciones = signal<Notificacion[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.monitoreo.notificaciones().subscribe({
      next: (r) => this.notificaciones.set(r.resultados),
      error: (e: ErrorMonitoreo) => this.error.set(e.detalle ?? 'Error al cargar las notificaciones.'),
      complete: () => this.cargando.set(false),
    });
  }

  marcar(n: Notificacion, estado: 'revisada' | 'resuelta'): void {
    this.monitoreo.marcarNotificacion(n.id, estado).subscribe({
      next: () => {
        if (estado === 'resuelta') {
          this.notificaciones.update((lista) => lista.filter((x) => x.id !== n.id));
        } else {
          this.notificaciones.update((lista) =>
            lista.map((x) => (x.id === n.id ? { ...x, estado, leida: true } : x)),
          );
        }
      },
      error: (e: ErrorMonitoreo) => this.error.set(e.detalle ?? 'No se pudo marcar la notificacion.'),
    });
  }
}
