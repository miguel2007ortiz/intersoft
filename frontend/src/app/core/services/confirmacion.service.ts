import { Injectable, signal } from '@angular/core';

/** Texto y aspecto de una confirmacion pendiente. */
export interface PeticionConfirmacion {
  titulo: string;
  mensaje: string;
  /** Texto del boton que confirma (por defecto "Confirmar"). */
  confirmar?: string;
  /** Texto del boton que cancela (por defecto "Cancelar"). */
  cancelar?: string;
  /** true = accion destructiva: el boton se pinta en rojo y el dialogo
   * avisa que no se puede deshacer. */
  destructivo?: boolean;
}

interface ConfirmacionAbierta extends PeticionConfirmacion {
  resolver: (acepto: boolean) => void;
}

/** Reemplaza al `confirm()` nativo del navegador, que bloquea el hilo, no
 * se puede estilizar, ignora el tema oscuro y en movil aparece como un
 * cuadro del sistema ajeno a la aplicacion.
 *
 * Uso:
 *   if (!await this.confirmacion.pedir({ titulo, mensaje })) return;
 *
 * El dialogo lo dibuja <app-confirmacion>, montado una sola vez en la raiz. */
@Injectable({ providedIn: 'root' })
export class ConfirmacionService {
  /** Confirmacion en pantalla; null = ninguna. */
  readonly abierta = signal<ConfirmacionAbierta | null>(null);

  /** Muestra el dialogo y resuelve a true si el usuario acepta. */
  pedir(peticion: PeticionConfirmacion): Promise<boolean> {
    // Si ya hay una abierta se cancela: nunca se apilan dos dialogos.
    this.responder(false);
    return new Promise<boolean>((resolver) => {
      this.abierta.set({ ...peticion, resolver });
    });
  }

  /** Cierra la confirmacion actual entregando la respuesta a quien la pidio. */
  responder(acepto: boolean): void {
    const actual = this.abierta();
    if (!actual) return;
    this.abierta.set(null);
    actual.resolver(acepto);
  }
}
