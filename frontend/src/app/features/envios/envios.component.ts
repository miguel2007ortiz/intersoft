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
  template: `
    <app-panel-shell>
      <div class="envios">
        <header class="envios-header">
          <h1>Envios</h1>
          <span class="contador">{{ envios().length }} en esta lista</span>
        </header>

        <section class="filtros">
          <select
            [(ngModel)]="filtroEstado"
            (ngModelChange)="cargarEnvios()"
            class="input input-estado"
            aria-label="Filtrar por estado"
          >
            <option value="">Todos los estados</option>
            @for (e of ENVIO_ESTADOS; track e.valor) {
              <option [value]="e.valor">{{ e.etiqueta }}</option>
            }
          </select>
        </section>

        @if (cargando()) {
          <p class="cargando">Cargando envios...</p>
        } @else if (error()) {
          <app-estado-vacio
            tipo="error"
            titulo="No pudimos cargar los envios"
            [mensaje]="error()"
            accionTexto="Reintentar"
            (accion)="cargarEnvios()"
          ></app-estado-vacio>
        } @else if (!envios().length) {
          @if (filtroEstado) {
            <app-estado-vacio
              tipo="busqueda"
              titulo="Sin envios en ese estado"
              mensaje="Prueba con otro estado o limpia el filtro."
            ></app-estado-vacio>
          } @else {
            <app-estado-vacio
              tipo="vacio"
              titulo="No hay envios"
              mensaje="Las ventas del marketplace con direccion de entrega apareceran aqui."
            ></app-estado-vacio>
          }
        } @else {
          <div class="lista">
            @for (env of envios(); track env.id) {
              <article class="envio-card aparecer">
                <header class="envio-cabecera">
                  <div>
                    <strong class="factura">{{ env.numero_factura }}</strong>
                    <span class="cliente">{{ env.cliente_nombre }}</span>
                  </div>
                  <span class="badge" [class]="'estado-' + env.estado">{{
                    env.estado_display
                  }}</span>
                </header>

                <div class="envio-datos">
                  <p class="direccion">
                    {{ env.direccion }}, {{ env.ciudad
                    }}{{ env.departamento ? ', ' + env.departamento : '' }}
                  </p>
                  <p class="guia">
                    @if (env.transportadora || env.numero_guia) {
                      <span>{{ env.transportadora || 'Sin transportadora' }}</span>
                      <span>Guia: {{ env.numero_guia || '—' }}</span>
                    } @else {
                      <span>Transportadora y guia por asignar</span>
                    }
                  </p>
                  @if (env.fecha_entrega_estimada) {
                    <p class="entrega">
                      Entrega estimada: {{ env.fecha_entrega_estimada | date: 'd MMM y' }}
                    </p>
                  }
                </div>

                <footer class="envio-pie">
                  <button type="button" class="btn-gestionar" (click)="gestionar(env)">
                    Gestionar envio
                  </button>
                </footer>
              </article>
            }
          </div>
        }
      </div>

      <!-- Modal de gestion -->
      @if (envioEditando(); as env) {
        <div class="modal-overlay" (click)="cancelar()">
          <div class="modal" role="dialog" aria-modal="true" (click)="$event.stopPropagation()">
            <h2>Gestionar envio</h2>
            <p class="modal-factura">
              <strong>{{ env.numero_factura }}</strong> — {{ env.cliente_nombre }}
            </p>

            <div class="modal-estado">
              <span class="badge" [class]="'estado-' + env.estado">{{ env.estado_display }}</span>
            </div>

            @if (estadosSiguientes().length) {
              <fieldset class="modal-transiciones">
                <legend>Avanzar estado</legend>
                <div class="transiciones">
                  @for (siguiente of estadosSiguientes(); track siguiente) {
                    <button
                      type="button"
                      class="btn-transicion"
                      [class.seleccionado]="nuevoEstado() === siguiente"
                      (click)="elegirEstado(siguiente)"
                    >
                      {{ etiquetaEstado(siguiente) }}
                    </button>
                  }
                </div>
              </fieldset>
            } @else {
              <p class="estado-terminal">Este envio esta en un estado final.</p>
            }

            <label for="transportadora">Transportadora</label>
            <input
              id="transportadora"
              type="text"
              [(ngModel)]="transportadora"
              class="input"
              placeholder="Ej: Servientrega"
            />

            <label for="numero-guia">Numero de guia</label>
            <input
              id="numero-guia"
              type="text"
              [(ngModel)]="numeroGuia"
              class="input"
              placeholder="Ej: SV-123456"
            />

            <label for="fecha-estimada">Fecha estimada de entrega</label>
            <input id="fecha-estimada" type="date" [(ngModel)]="fechaEstimada" class="input" />

            <label for="notas-envio">Notas internas</label>
            <textarea
              id="notas-envio"
              [(ngModel)]="notas"
              class="input notas"
              rows="3"
              placeholder="Observaciones solo para el equipo de la empresa..."
            ></textarea>

            @if (errorGuardado()) {
              <div class="error-box" role="alert">{{ errorGuardado() }}</div>
            }

            <div class="modal-acciones">
              <button type="button" class="btn-cancelar" (click)="cancelar()">Cancelar</button>
              <button
                type="button"
                class="btn-guardar"
                [disabled]="guardando()"
                (click)="guardar()"
              >
                @if (guardando()) {
                  Guardando...
                } @else {
                  Guardar cambios
                }
              </button>
            </div>
          </div>
        </div>
      }
    </app-panel-shell>
  `,
  styles: [
    `
      .envios {
        max-width: 900px;
        margin: 0 auto;
        padding: var(--e5) var(--e4);
      }
      .envios-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: var(--e5);
      }
      .envios-header h1 {
        margin: 0;
        font-size: clamp(22px, 4vw, 28px);
      }
      .contador {
        background: var(--primario-suave);
        color: var(--primario);
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 600;
      }

      .filtros {
        margin-bottom: var(--e4);
      }
      .input {
        padding: 10px 14px;
        border: 1px solid var(--linea);
        border-radius: 8px;
        font: inherit;
        font-size: 14px;
        background: #fff;
        width: 100%;
      }
      .input:focus {
        outline: none;
        border-color: var(--primario);
      }
      .input-estado {
        max-width: 260px;
      }

      .cargando {
        color: var(--gris);
        text-align: center;
        padding: var(--e6);
      }

      .lista {
        display: flex;
        flex-direction: column;
        gap: var(--e3);
      }

      .envio-card {
        background: #fff;
        border: 1px solid var(--linea);
        border-radius: 12px;
        padding: var(--e4);
        transition: box-shadow 0.15s;
      }
      .envio-card:hover {
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
      }
      .envio-cabecera {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: var(--e2);
        margin-bottom: var(--e3);
        padding-bottom: var(--e3);
        border-bottom: 1px solid var(--linea);
      }
      .factura {
        font-family: monospace;
      }
      .cliente {
        display: block;
        font-size: 12.5px;
        color: var(--gris);
        margin-top: 2px;
      }

      .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }
      .estado-pendiente {
        background: #fef9ec;
        color: #b54708;
      }
      .estado-preparando {
        background: #eff6ff;
        color: #1d4ed8;
      }
      .estado-despachado {
        background: #f5f3ff;
        color: #6d28d9;
      }
      .estado-en_transito {
        background: #eef2ff;
        color: #4338ca;
      }
      .estado-entregado {
        background: #ecfdf3;
        color: #067647;
      }
      .estado-no_entregado {
        background: #fef3f2;
        color: #b42318;
      }
      .estado-devuelto {
        background: #f1f5f9;
        color: #475569;
      }

      .envio-datos {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-bottom: var(--e3);
      }
      .envio-datos p {
        margin: 0;
        font-size: 14px;
        color: var(--tinta);
      }
      .guia {
        display: flex;
        gap: var(--e4);
        font-size: 13px !important;
        color: var(--gris) !important;
      }
      .entrega {
        font-size: 13px !important;
        color: var(--gris) !important;
      }

      .envio-pie {
        display: flex;
        justify-content: flex-end;
      }
      .btn-gestionar {
        padding: 7px 16px;
        border: 1px solid var(--linea);
        background: #fff;
        border-radius: 8px;
        cursor: pointer;
        font: inherit;
        font-size: 13px;
        font-weight: 600;
      }
      .btn-gestionar:hover {
        border-color: var(--primario);
        color: var(--primario);
      }

      .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.5);
        display: grid;
        place-items: center;
        z-index: 1000;
      }
      .modal {
        background: #fff;
        border-radius: 14px;
        padding: var(--e6);
        width: min(480px, 90vw);
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
      }
      .modal h2 {
        margin: 0 0 var(--e2);
      }
      .modal-factura {
        margin: 0 0 var(--e3);
        font-size: 14px;
        color: var(--gris);
      }
      .modal label {
        display: block;
        margin-top: var(--e3);
        margin-bottom: var(--e2);
        font-weight: 600;
        font-size: 14px;
      }
      .modal .input {
        margin-bottom: 0;
      }
      .notas {
        resize: vertical;
      }
      .modal-estado {
        margin-bottom: var(--e3);
      }
      .estado-terminal {
        font-size: 13px;
        color: var(--gris);
        margin: 0 0 var(--e2);
      }

      .modal-transiciones {
        border: 0;
        padding: 0;
        margin: 0 0 var(--e2);
      }
      .modal-transiciones legend {
        font-weight: 600;
        font-size: 14px;
        margin-bottom: var(--e2);
        padding: 0;
      }
      .transiciones {
        display: flex;
        flex-wrap: wrap;
        gap: var(--e2);
      }
      .btn-transicion {
        padding: 7px 14px;
        border: 1px solid var(--linea);
        background: #fff;
        border-radius: 8px;
        cursor: pointer;
        font: inherit;
        font-size: 12.5px;
        font-weight: 600;
      }
      .btn-transicion:hover {
        border-color: var(--primario);
        color: var(--primario);
      }
      .btn-transicion.seleccionado {
        background: var(--primario);
        border-color: var(--primario);
        color: #fff;
      }

      .error-box {
        background: #fef3f2;
        border: 1px solid #fecdca;
        border-radius: 8px;
        padding: 10px 14px;
        margin-top: var(--e3);
        color: #b42318;
        font-size: 13px;
      }
      .modal-acciones {
        display: flex;
        justify-content: flex-end;
        gap: var(--e3);
        margin-top: var(--e4);
      }
      .btn-cancelar {
        padding: 10px 20px;
        border: 1px solid var(--linea);
        background: #fff;
        border-radius: 8px;
        cursor: pointer;
        font: inherit;
      }
      .btn-guardar {
        padding: 10px 20px;
        border: 0;
        background: var(--primario);
        color: #fff;
        border-radius: 8px;
        cursor: pointer;
        font: inherit;
        font-weight: 600;
      }
      .btn-guardar:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    `,
  ],
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
