import { Component, ElementRef, HostListener, effect, inject, viewChild } from '@angular/core';
import { ConfirmacionService } from '../../core/services/confirmacion.service';

/** Dialogo de confirmacion de la aplicacion, en reemplazo del `confirm()`
 * nativo. Se monta una sola vez en la raiz y lo abre ConfirmacionService.
 *
 * Accesibilidad:
 * - role="alertdialog" + aria-modal, con titulo y mensaje enlazados.
 * - El foco entra al dialogo y queda atrapado dentro mientras esta abierto.
 * - Escape cancela; al cerrar, el foco vuelve al boton que lo abrio, para
 *   no perder el lugar en la pagina (importante con lector de pantalla).
 * - En una accion destructiva el foco arranca en "Cancelar", nunca en el
 *   boton que borra. */
@Component({
  selector: 'app-confirmacion',
  template: `
    @if (confirmacion.abierta(); as datos) {
      <div class="capa" (click)="cancelar()">
        <div #panel class="dialogo" role="alertdialog" aria-modal="true"
             aria-labelledby="confirmacion-titulo"
             aria-describedby="confirmacion-mensaje"
             (click)="$event.stopPropagation()">
          <h2 id="confirmacion-titulo" class="titulo">
            @if (datos.destructivo) {
              <span class="icono-alerta" aria-hidden="true">!</span>
            }
            {{ datos.titulo }}
          </h2>
          <p id="confirmacion-mensaje" class="mensaje">{{ datos.mensaje }}</p>
          @if (datos.destructivo) {
            <p class="aviso-destructivo">Esta accion no se puede deshacer.</p>
          }
          <div class="acciones">
            <button #botonCancelar type="button" class="btn btn-cancelar"
                    (click)="cancelar()">
              {{ datos.cancelar ?? 'Cancelar' }}
            </button>
            <button #botonConfirmar type="button" class="btn"
                    [class.btn-destructivo]="datos.destructivo"
                    [class.btn-confirmar]="!datos.destructivo"
                    (click)="confirmar()">
              {{ datos.confirmar ?? 'Confirmar' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .capa {
      position: fixed; inset: 0; z-index: 10000;
      display: flex; align-items: center; justify-content: center;
      padding: var(--e4);
      background: rgba(16, 24, 40, .55);
      backdrop-filter: blur(2px);
      animation: aparecer .12s ease-out;
    }
    .dialogo {
      background: var(--tarjeta); color: var(--tinta);
      border: 1px solid var(--linea); border-radius: var(--radio);
      box-shadow: var(--sombra);
      padding: var(--e5);
      max-width: 440px; width: 100%;
      animation: subir .15s ease-out;
    }
    .titulo {
      margin: 0 0 var(--e3);
      font-size: 18px; line-height: 1.3;
      display: flex; align-items: center; gap: var(--e2);
    }
    .icono-alerta {
      flex: none;
      width: 24px; height: 24px; border-radius: 50%;
      background: var(--error-fondo); color: var(--error);
      display: grid; place-items: center;
      font-weight: 700; font-size: 15px;
    }
    .mensaje { margin: 0; color: var(--gris); font-size: 14px; line-height: 1.55; }
    .aviso-destructivo {
      margin: var(--e3) 0 0; padding: var(--e2) var(--e3);
      background: var(--error-fondo); border: 1px solid var(--error-borde);
      border-radius: var(--e2); color: var(--error);
      font-size: 13px; font-weight: 600;
    }
    .acciones {
      display: flex; justify-content: flex-end; gap: var(--e2);
      margin-top: var(--e5); flex-wrap: wrap;
    }
    .btn {
      padding: 9px 18px; border-radius: var(--e2);
      border: 1px solid var(--linea); background: var(--blanco); color: var(--tinta);
      font: inherit; font-size: 14px; font-weight: 600; cursor: pointer;
      transition: filter .15s, border-color .15s;
    }
    .btn:hover { filter: brightness(.97); }
    .btn:focus-visible { outline: 2px solid var(--primario); outline-offset: 2px; }
    .btn-confirmar { background: var(--primario); border-color: var(--primario); color: #fff; }
    .btn-destructivo { background: var(--error); border-color: var(--error); color: #fff; }

    @keyframes aparecer { from { opacity: 0 } to { opacity: 1 } }
    @keyframes subir {
      from { opacity: 0; transform: translateY(6px) scale(.99) }
      to { opacity: 1; transform: none }
    }
    /* Respeta a quien pidio menos movimiento en el sistema. */
    @media (prefers-reduced-motion: reduce) {
      .capa, .dialogo { animation: none; }
    }
  `],
})
export class ConfirmacionComponent {
  readonly confirmacion = inject(ConfirmacionService);

  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');
  private readonly botonCancelar = viewChild<ElementRef<HTMLButtonElement>>('botonCancelar');
  private readonly botonConfirmar = viewChild<ElementRef<HTMLButtonElement>>('botonConfirmar');

  /** Elemento que tenia el foco antes de abrir, para devolverselo al cerrar. */
  private origenDelFoco: HTMLElement | null = null;

  constructor() {
    effect(() => {
      const datos = this.confirmacion.abierta();
      if (!datos) return;
      this.origenDelFoco = document.activeElement as HTMLElement | null;
      // En una accion destructiva el foco arranca en "Cancelar": un Enter
      // por inercia no debe borrar nada.
      const inicial = datos.destructivo ? this.botonCancelar() : this.botonConfirmar();
      inicial?.nativeElement.focus();
    });
  }

  confirmar(): void { this.cerrar(true); }

  cancelar(): void { this.cerrar(false); }

  @HostListener('document:keydown.escape')
  cancelarConEscape(): void {
    if (this.confirmacion.abierta()) this.cancelar();
  }

  /** Mantiene el foco dentro del dialogo: Tab en el ultimo boton vuelve al
   * primero y Shift+Tab en el primero salta al ultimo. */
  @HostListener('document:keydown', ['$event'])
  atraparTabulacion(evento: KeyboardEvent): void {
    const panel = this.panel()?.nativeElement;
    if (evento.key !== 'Tab' || !this.confirmacion.abierta() || !panel) return;
    const focusables = panel.querySelectorAll<HTMLElement>('button');
    if (!focusables.length) return;
    const primero = focusables[0];
    const ultimo = focusables[focusables.length - 1];
    const activo = document.activeElement;
    if (evento.shiftKey && activo === primero) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && activo === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }

  private cerrar(acepto: boolean): void {
    this.confirmacion.responder(acepto);
    this.origenDelFoco?.focus();
    this.origenDelFoco = null;
  }
}
