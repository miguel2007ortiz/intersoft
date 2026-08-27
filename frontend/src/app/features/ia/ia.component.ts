import { Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { IaService } from '../../core/services/ia.service';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { ErrorIA, MensajeIA } from '../../core/models/ia.model';

/** Fase 8: asistente IA (ADMINISTRADOR y EMPLEADO).
 * Chat con historial por sesion, contexto de la empresa y reenvio al
 * reintentar cuando el motor responde con error. */

@Component({
  selector: 'app-ia',
  imports: [FormsModule, PanelShellComponent],
  templateUrl: './ia.component.html',
  styleUrl: './ia.component.css',
})
export class IaComponent {
  readonly auth = inject(AuthService);
  private readonly ia = inject(IaService);
  private readonly zonaMensajes = viewChild<ElementRef<HTMLDivElement>>('zonaMensajes');

  readonly mensajes = signal<MensajeIA[]>([]);
  readonly conversacionId = signal<string | undefined>(undefined);
  readonly texto = signal('');
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly soloUsuario = signal(true);

  constructor() {
    this.mensajes.set(this.reintentarPendiente());
  }

  private reintentarPendiente(): MensajeIA[] {
    const encolar = localStorage.getItem('ia.reintentar');
    if (!encolar) return this.mensajes();
    try {
      const { conversacion, mensajesOrdenados } = JSON.parse(encolar);
      localStorage.removeItem('ia.reintentar');
      this.conversacionId.set(conversacion?.id);
      return mensajesOrdenados ?? this.mensajes();
    } catch {
      return this.mensajes();
    }
  }

  esEscritor(rol: string): boolean {
    return rol === 'usuario';
  }

  enviar(): void {
    const texto = this.texto().trim();
    if (!texto || this.cargando()) return;
    this.cargando.set(true);
    this.error.set(null);
    const conversacionId = this.conversacionId();
    this.ia.enviar(texto, conversacionId).subscribe({
      next: (r) => {
        this.texto.set('');
        this.conversacionId.set(r.conversacion.id);
        this.mensajes.set(r.conversacion.mensajes);
        this.cargando.set(false);
        this.soloUsuario.set(false);
        this.scrollAbajo();
      },
      error: (e: ErrorIA) => {
        this.cargando.set(false);
        if (e.codigo === 'IA_NO_DISPONIBLE' && e.conversacion) {
          // El motor fallo: conserva la conversacion para reintentar.
          this.conversacionId.set(e.conversacion.id);
          this.error.set(e.detalle);
          this.guardarReintento(e.conversacion);
        } else {
          this.error.set(e.detalle ?? 'No se pudo enviar el mensaje.');
        }
      },
    });
  }

  private guardarReintento(conversacion: {
    id: string; mensajes: MensajeIA[];
  }): void {
    const mensajesOrdenados = [...conversacion.mensajes].sort((a, b) =>
      a.created_at.localeCompare(b.created_at));
    localStorage.setItem('ia.reintentar', JSON.stringify({
      conversacion: { id: conversacion.id },
      mensajesOrdenados,
    }));
  }

  nuevaConversacion(): void {
    this.mensajes.set([]);
    this.conversacionId.set(undefined);
    this.error.set(null);
    this.soloUsuario.set(true);
    this.texto.set('');
  }

  private scrollAbajo(): void {
    const zona = this.zonaMensajes()?.nativeElement;
    if (zona) zona.scrollTop = zona.scrollHeight;
  }
}
