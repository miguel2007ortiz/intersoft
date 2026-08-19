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
