import { DatePipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { CatalogoService } from '../../core/services/catalogo.service';
import { Notificacion } from '../../core/models/catalogo.model';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-alertas',
  imports: [DatePipe, PanelShellComponent],
  template: `
    <app-panel-shell>
      <div class="alertas">
        <header class="alertas-header">
          <h1>Alertas de Stock</h1>
          <span class="contador">{{ alertas().length }} activas</span>
        </header>

        @if (cargando()) {
          <p class="cargando">Cargando alertas...</p>
        } @else if (!alertas().length) {
          <div class="vacio">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor"
                 stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2z" />
              <path d="M18 16v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
            </svg>
            <p>No hay alertas pendientes.</p>
          </div>
        } @else {
          <div class="lista-alertas">
            @for (a of alertas(); track a.id) {
              <div class="alerta-card">
                <div class="alerta-icono">
                  <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2z" />
                    <path d="M18 16v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
                  </svg>
                </div>
                <div class="alerta-info">
                  <p class="alerta-mensaje">{{ a.mensaje }}</p>
                  <span class="alerta-fecha">{{ a.created_at | date:'dd/MM/yy HH:mm' }}</span>
                </div>
                <div class="alerta-acciones">
                  <button type="button" class="btn-revisar" (click)="marcarRevisada(a)">
                    Marcar resuelta
                  </button>
                </div>
              </div>
            }
          </div>
        }
      </div>
    </app-panel-shell>
  `,
  styles: [`
    .alertas { max-width: 800px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .alertas-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--e5); }
    .alertas-header h1 { margin: 0; font-size: clamp(22px, 4vw, 28px); }
    .contador {
      background: #fef3f2; color: #b42318; padding: 4px 12px;
      border-radius: 999px; font-size: 13px; font-weight: 600;
    }

    .cargando { color: var(--gris); text-align: center; padding: var(--e6); }

    .vacio {
      text-align: center; padding: var(--e8) var(--e4); color: var(--gris);
    }
    .vacio svg { margin-bottom: var(--e3); opacity: .4; }
    .vacio p { margin: 0; font-size: 16px; }

    .lista-alertas { display: flex; flex-direction: column; gap: var(--e3); }

    .alerta-card {
      display: flex; align-items: flex-start; gap: var(--e4);
      background: #fff; border: 1px solid #fecdca; border-left: 4px solid #f97316;
      border-radius: 10px; padding: var(--e4);
      transition: box-shadow .15s;
    }
    .alerta-card:hover { box-shadow: 0 4px 12px rgba(249,115,22,.1); }

    .alerta-icono { color: #f97316; flex-shrink: 0; margin-top: 2px; }
    .alerta-info { flex: 1; }
    .alerta-mensaje { margin: 0 0 4px; font-size: 14px; line-height: 1.5; }
    .alerta-fecha { font-size: 12px; color: var(--gris); }

    .btn-revisar {
      padding: 6px 14px; border: 1px solid #d1fadf; background: #ecfdf3;
      color: #067647; border-radius: 6px; cursor: pointer; font: inherit;
      font-size: 12px; font-weight: 600; white-space: nowrap;
    }
    .btn-revisar:hover { background: #d1fadf; }
  `],
})
export class AlertasComponent implements OnInit {
  private readonly catalogo = inject(CatalogoService);

  readonly alertas = signal<Notificacion[]>([]);
  readonly cargando = signal(true);

  ngOnInit(): void {
    this.cargarAlertas();
  }

  cargarAlertas(): void {
    this.catalogo.listarAlertas().subscribe({
      next: (r) => { this.alertas.set(r.resultados); this.cargando.set(false); },
      error: () => this.cargando.set(false),
    });
  }

  marcarRevisada(alerta: Notificacion): void {
    this.catalogo.marcarAlertaRevisada(alerta.id).subscribe({
      next: () => {
        this.alertas.update(a => a.filter(x => x.id !== alerta.id));
      },
    });
  }
}
