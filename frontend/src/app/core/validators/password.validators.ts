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
