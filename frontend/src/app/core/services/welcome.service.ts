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
