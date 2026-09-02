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