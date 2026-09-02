import { DestroyRef } from '@angular/core';

/** setTimeout que se cancela solo al destruirse el contenedor (p. ej.
 * avisos de "exito" auto-ocultables) para no llamar a signals de un
 * componente ya destruido. */
export function programarAviso(
  destroyRef: DestroyRef,
  callback: () => void,
  ms: number,
): number {
  const manejador = setTimeout(callback, ms);
  destroyRef.onDestroy(() => clearTimeout(manejador));
  return manejador;
}

/** Agrupa llamadas rapidas (p. ej. tecla a tecla en un buscador) en una
 * sola, disparada `ms` despues de la ultima. Evita golpear la API en cada
 * tecla y las condiciones de carrera de respuestas fuera de orden. Se
 * cancela sola al destruirse el componente. */
export function debounce(
  destroyRef: DestroyRef,
  callback: () => void,
  ms: number,
): () => void {
  let manejador: ReturnType<typeof setTimeout> | undefined;
  destroyRef.onDestroy(() => { if (manejador) clearTimeout(manejador); });
  return () => {
    if (manejador) clearTimeout(manejador);
    manejador = setTimeout(callback, ms);
  };
}