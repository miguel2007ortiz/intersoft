/**
 * emailUnicoValidator — comprueba contra el backend si un correo ya existe
 *
 * Que hace: validador asincrono de formularios reactivos. Espera 400 ms desde
 * la ultima tecla y consulta /auth/email-disponible/; si el correo esta en uso
 * marca el control con el error `emailEnUso`.
 * Donde se usa: formularios de registro (empresa y comprador).
 * Por que asi: el `timer(400)` evita una peticion por cada letra tecleada. Si
 * la consulta falla se devuelve `null` (valido): no se le bloquea el registro
 * a alguien por un problema de red; el backend rechazara el duplicado igual.
 */

import { AbstractControl, AsyncValidatorFn, ValidationErrors } from '@angular/forms';
import { Observable, catchError, map, of, switchMap, timer } from 'rxjs';
import { AuthService } from '../services/auth.service';

export function emailUnicoValidator(auth: AuthService): AsyncValidatorFn {
  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    const email = (control.value ?? '').trim();
    if (!email || control.hasError('email')) return of(null);
    return timer(400).pipe(
      switchMap(() => auth.emailDisponible(email)),
      map((disponible) => (disponible ? null : { emailEnUso: true })),
      catchError(() => of(null)),
    );
  };
}
