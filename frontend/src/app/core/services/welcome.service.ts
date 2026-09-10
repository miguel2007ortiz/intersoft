/**
 * WelcomeService — saludo de bienvenida tras iniciar sesion
 *
 * Que hace: enciende durante 2,4 segundos el cartel de bienvenida con el
 * nombre del usuario y lo apaga solo.
 * Donde se usa: lo dispara el login; lo pinta <app-welcome-overlay>, montado
 * en app.html.
 * Por que asi: el estado vive en el servicio y no en el componente, porque
 * quien decide mostrarlo (login) y quien lo dibuja (overlay en la raiz) son
 * dos piezas distintas del arbol.
 */

import { Injectable, signal } from '@angular/core';

const DURACION_MS = 2400;

@Injectable({ providedIn: 'root' })
export class WelcomeService {
  private readonly _activo = signal(false);
  private readonly _nombre = signal('');
  private temporizador: ReturnType<typeof setTimeout> | null = null;

  readonly activo = this._activo.asReadonly();
  readonly nombre = this._nombre.asReadonly();

  mostrar(nombre: string): void {
    if (this.temporizador) clearTimeout(this.temporizador);
    this._nombre.set(nombre);
    this._activo.set(true);
    this.temporizador = setTimeout(() => this._activo.set(false), DURACION_MS);
  }

  ocultar(): void {
    if (this.temporizador) clearTimeout(this.temporizador);
    this._activo.set(false);
  }
}
