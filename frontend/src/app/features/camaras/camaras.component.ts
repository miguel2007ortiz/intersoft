import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MonitoreoService } from '../../core/services/monitoreo.service';
import { Camara, CamaraEscritura, ErrorMonitoreo, GrabacionCamara } from '../../core/models/monitoreo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

/** Fase 9: panel de camaras de vigilancia (solo ADMINISTRADOR).
 * Muestra el video en vivo y permite consultar grabaciones historicas
 * por fecha/hora desde el servidor de almacenamiento. */
@Component({
  selector: 'app-camaras',
  imports: [FormsModule, PanelShellComponent],
  templateUrl: './camaras.component.html',
  styleUrl: './camaras.component.css',
})
export class CamarasComponent implements OnInit {
  private readonly monitoreo = inject(MonitoreoService);

  readonly camaras = signal<Camara[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  // Formulario de creacion
  readonly mostrandoForm = signal(false);
  readonly nombre = signal('');
  readonly ubicacion = signal('');
  readonly urlStream = signal('');
  readonly guardando = signal(false);

  // Grabadora historica
  readonly camaraActiva = signal<Camara | null>(null);
  readonly fecha = signal('');
  readonly hora = signal('12:00');
  readonly grabacion = signal<GrabacionCamara | null>(null);
  readonly consultando = signal(false);

  ngOnInit(): void {
    this.cargarCamaras();
  }

  cargarCamaras(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.monitoreo.camaras().subscribe({
      next: (r) => this.camaras.set(r.resultados),
      error: (e: ErrorMonitoreo) => this.error.set(e.detalle ?? 'Error al cargar las camaras.'),
      complete: () => this.cargando.set(false),
    });
  }

  abrirFormulario(): void { this.mostrandoForm.set(true); }
  cerrarFormulario(): void { this.mostrandoForm.set(false); }

  crearCamara(): void {
    if (!this.nombre().trim()) return;
    this.guardando.set(true);
    this.error.set(null);
    const datos: CamaraEscritura = {
      nombre: this.nombre().trim(),
      ubicacion: this.ubicacion().trim(),
      url_stream: this.urlStream().trim(),
    };
    this.monitoreo.crearCamara(datos).subscribe({
      next: () => {
        this.cerrarFormulario();
        this.nombre.set(''); this.ubicacion.set(''); this.urlStream.set('');
        this.cargarCamaras();
      },
      error: (e: ErrorMonitoreo) => { this.error.set(e.detalle ?? 'No se pudo crear la camara.'); this.guardando.set(false); },
      complete: () => this.guardando.set(false),
    });
  }

  alternarActiva(c: Camara): void {
    this.monitoreo.editarCamara(c.id, { activa: !c.activa }).subscribe({
      next: () => this.cargarCamaras(),
      error: (e: ErrorMonitoreo) => this.error.set(e.detalle ?? 'No se pudo actualizar la camara.'),
    });
  }

  eliminar(c: Camara): void {
    if (!confirm(`Eliminar la camara "${c.nombre}"?`)) return;
    this.monitoreo.eliminarCamara(c.id).subscribe({
      next: () => this.cargarCamaras(),
      error: (e: ErrorMonitoreo) => this.error.set(e.detalle ?? 'No se pudo eliminar la camara.'),
    });
  }

  seleccionar(c: Camara): void {
    this.camaraActiva.set(c);
    this.grabacion.set(null);
  }

  cerrarGrabadora(): void { this.camaraActiva.set(null); this.grabacion.set(null); }

  consultarGrabacion(): void {
    const c = this.camaraActiva();
    if (!c || !this.fecha()) return;
    this.consultando.set(true);
    this.grabacion.set(null);
    this.monitoreo.grabacion(c.id, this.fecha(), this.hora()).subscribe({
      next: (g) => { this.grabacion.set(g); this.consultando.set(false); },
      error: (e: ErrorMonitoreo) => {
        const detalle = e.detalle ?? 'No se encontro la grabacion.';
        this.grabacion.set({ disponible: false, detalle });
        this.consultando.set(false);
      },
    });
  }
}
