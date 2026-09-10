/**
 * TemaService — modo claro y modo noche
 *
 * Que hace: guarda la preferencia en localStorage y pone o quita la clase
 * `oscuro` en el <body>.
 * Donde se usa: el interruptor de la topbar y la pantalla de configuracion.
 * Por que asi: aplicarlo en el <body> y no en cada componente permite que un
 * unico bloque de variables CSS cambie los colores de toda la aplicacion. Al
 * arrancar se lee la preferencia antes de pintar, para no ver un fogonazo
 * blanco antes del modo noche.
 */

import { Injectable, signal } from '@angular/core';

export type Tema = 'claro' | 'noche';

const CLAVE_TEMA = 'intersoft.tema';

/** Modo noche: guarda la preferencia y aplica la clase 'noche' al <body>. */
@Injectable({ providedIn: 'root' })
export class TemaService {
  readonly tema = signal<Tema>(this.leerGuardado());

  constructor() {
    this.aplicar(this.tema());
  }

  alternar(): void {
    const nuevo: Tema = this.tema() === 'noche' ? 'claro' : 'noche';
    this.tema.set(nuevo);
    localStorage.setItem(CLAVE_TEMA, nuevo);
    this.aplicar(nuevo);
  }

  private aplicar(tema: Tema): void {
    document.body.classList.toggle('noche', tema === 'noche');
  }

  private leerGuardado(): Tema {
    return localStorage.getItem(CLAVE_TEMA) === 'noche' ? 'noche' : 'claro';
  }
}
