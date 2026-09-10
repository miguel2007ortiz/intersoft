/**
 * Validadores de contrasena — mismas reglas que exige el backend
 *
 * Que hace: comprueba longitud, mayuscula, minuscula, numero y que las dos
 * contrasenas coincidan, y devuelve la lista de requisitos que faltan.
 * Donde se usa: registro, cambio de contrasena y restablecer contrasena.
 * Por que asi: se replica la regla del servidor para poder decir al usuario
 * que le falta MIENTRAS escribe, en vez de esperar al 400 del backend. El
 * backend sigue siendo el que manda; esto es solo aviso temprano.
 */

import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export const fuerzaPassword: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const valor: string = control.value ?? '';
  if (!valor) return null;
  const faltantes: string[] = [];
  if (valor.length < 8) faltantes.push('8 caracteres');
  if (!/[A-Z]/.test(valor)) faltantes.push('una mayuscula');
  if (!/[a-z]/.test(valor)) faltantes.push('una minuscula');
  if (!/[0-9]/.test(valor)) faltantes.push('un numero');
  return faltantes.length ? { fuerza: { faltantes } } : null;
};

export function passwordsIguales(campoA: string, campoB: string): ValidatorFn {
  return (grupo: AbstractControl): ValidationErrors | null => {
    const a = grupo.get(campoA)?.value;
    const b = grupo.get(campoB)?.value;
    if (!a || !b) return null;
    return a === b ? null : { passwordsDistintas: true };
  };
}
