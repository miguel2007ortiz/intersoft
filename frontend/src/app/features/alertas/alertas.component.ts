import { DatePipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { CatalogoService } from '../../core/services/catalogo.service';
import { Notificacion } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-alertas',
  imports: [DatePipe, PanelShellComponent],
  templateUrl: './alertas.component.html',
  styleUrls: ['./alertas.component.css'],
})
export class AlertasComponent implements OnInit {
  private readonly catalogo = inject(CatalogoService);

  readonly alertas = signal<Notificacion[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly resolviendo = signal(false);

  ngOnInit(): void {
    this.cargarAlertas();
  }

  cargarAlertas(): void {
    this.cargando.set(true);
    this.catalogo.listarAlertas().subscribe({
      next: (r) => {
        this.alertas.set(r.resultados);
        this.error.set(null);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle ?? 'No se pudo cargar la lista.');
        this.cargando.set(false);
      },
    });
  }

  marcarRevisada(alerta: Notificacion): void {
    if (this.resolviendo()) return;
    this.resolviendo.set(true);
    this.catalogo.marcarAlertaRevisada(alerta.id).subscribe({
      next: () => {
        this.alertas.update((a) => a.filter((x) => x.id !== alerta.id));
        this.resolviendo.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle ?? 'No se pudo marcar la alerta como revisada.');
        this.resolviendo.set(false);
      },
    });
  }
}
