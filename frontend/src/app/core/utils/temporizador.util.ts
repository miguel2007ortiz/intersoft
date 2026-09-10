/**
 * programarAviso y debounce — temporizadores que se limpian solos
 *
 * Que hace: `programarAviso(destroyRef, fn, ms)` es un setTimeout que se
 * cancela si el componente se destruye antes; `debounce` agrupa las llamadas
 * rapidas (teclear en un buscador) en una sola.
 * Donde se usa: mensajes de exito que se desvanecen y buscadores con retardo.
 * Por que asi: obligar a pasar el DestroyRef hace imposible olvidar la
 * limpieza; sin ella, un temporizador vivo escribe en un componente que ya no
 * existe y salta un error en consola.
 */

import { DestroyRef } from '@angular/core';

/** setTimeout que se cancela solo al destruirse el contenedor (p. ej.
 * avisos de "exito" auto-ocultables) para no llamar a signals de un
 * componente ya destruido. */
export function programarAviso(destroyRef: DestroyRef, callback: () => void, ms: number): number {
  const manejador = setTimeout(callback, ms);
  destroyRef.onDestroy(() => clearTimeout(manejador));
  return manejador;
}

/** Agrupa llamadas rapidas (p. ej. tecla a tecla en un buscador) en una
 * sola, disparada `ms` despues de la ultima. Evita golpear la API en cada
 * tecla y las condiciones de carrera de respuestas fuera de orden. Se
 * cancela sola al destruirse el componente. */
export function debounce(destroyRef: DestroyRef, callback: () => void, ms: number): () => void {
  let manejador: ReturnType<typeof setTimeout> | undefined;
  destroyRef.onDestroy(() => {
    if (manejador) clearTimeout(manejador);
  });
  return () => {
    if (manejador) clearTimeout(manejador);
    manejador = setTimeout(callback, ms);
  };
}
