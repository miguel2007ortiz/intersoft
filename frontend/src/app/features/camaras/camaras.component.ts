import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MonitoreoService } from '../../core/services/monitoreo.service';
import { Camara, CamaraEscritura, ErrorMonitoreo, Grabacion, GrabacionCamara } from '../../core/models/monitoreo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

/** Fase 9: panel de camaras de vigilancia (solo ADMINISTRADOR).
 * Muestra el video en vivo, el catalogo de grabaciones historicas
 * (metadatos sincronizados por `sincronizar_grabaciones`) y permite
 * consultar una sesion por fecha/hora. */
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

  // Catalogo de grabaciones de la camara activa
  readonly grabaciones = signal<Grabacion[]>([]);
  readonly grabacionesCargando = signal(false);
  readonly totalGrabaciones = signal(0);
  readonly paginaGrabaciones = signal(1);
  readonly totalPaginas = signal(1);

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
    this.paginaGrabaciones.set(1);
    this.cargarGrabaciones();
  }

  cerrarGrabadora(): void { this.camaraActiva.set(null); this.grabacion.set(null); }

  cargarGrabaciones(): void {
    const c = this.camaraActiva();
    if (!c) return;
    this.grabacionesCargando.set(true);
    this.monitoreo.grabacionesCamera(c.id, { pagina: this.paginaGrabaciones() }).subscribe({
      next: (r) => {
        this.grabaciones.set(r.resultados);
        this.totalGrabaciones.set(r.total);
        this.totalPaginas.set(r.total_paginas);
        this.grabacionesCargando.set(false);
      },
      error: (e: ErrorMonitoreo) => {
        this.error.set(e.detalle ?? 'No se pudo cargar el catalogo de grabaciones.');
        this.grabacionesCargando.set(false);
      },
    });
  }

  irPagina(pagina: number): void {
    if (pagina < 1 || pagina > this.totalPaginas()) return;
    this.paginaGrabaciones.set(pagina);
    this.cargarGrabaciones();
  }

  reproducir(g: Grabacion): void {
    if (!g.disponible) return;
    this.fecha.set(g.fecha);
    this.hora.set(g.hora.slice(0, 5));
    this.consultarGrabacion();
  }

  tamanoLegible(bytes: number): string {
    if (bytes >= 1 << 30) return `${(bytes / (1 << 30)).toFixed(1)} GB`;
    if (bytes >= 1 << 20) return `${(bytes / (1 << 20)).toFixed(1)} MB`;
    if (bytes >= 1 << 10) return `${(bytes / (1 << 10)).toFixed(0)} KB`;
    return `${bytes} B`;
  }

  duracionLegible(segundos: number): string {
    if (!segundos) return 'Duracion no registrada';
    const m = Math.floor(segundos / 60);
    const s = segundos % 60;
    return `${m} min ${s.toString().padStart(2, '0')} s`;
  }

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
