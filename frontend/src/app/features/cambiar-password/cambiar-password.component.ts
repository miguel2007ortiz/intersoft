import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthShellComponent } from '../../shared/layout/auth-shell/auth-shell.component';
import { AuthService } from '../../core/services/auth.service';
import { ErrorAuth } from '../../core/models/auth.model';
import { fuerzaPassword, passwordsIguales } from '../../core/validators/password.validators';

/** Pantalla de cambio de contrasena forzado (RN-09): la impone el backend
 * con Perfil.debe_cambiar_password (contrasena temporal de creacion/reset
 * por el ADMINISTRADOR). CambioPasswordMiddleware bloquea el resto de la
 * API con 403 hasta que se complete, y el interceptor redirige aqui. */
@Component({
  selector: 'app-cambiar-password',
  imports: [ReactiveFormsModule, AuthShellComponent],
  templateUrl: './cambiar-password.component.html',
  styleUrl: './cambiar-password.component.css',
})
export class CambiarPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly formulario = this.fb.nonNullable.group(
    {
      password_actual: ['', [Validators.required]],
      password_nueva: ['', [Validators.required, fuerzaPassword]],
      password_nueva2: ['', [Validators.required]],
    },
    { validators: passwordsIguales('password_nueva', 'password_nueva2') },
  );

  readonly cargando = signal(false);
  readonly error = signal<ErrorAuth | null>(null);
  readonly verPassword = signal(false);

  get passwordActual() {
    return this.formulario.controls.password_actual;
  }

  get passwordNueva() {
    return this.formulario.controls.password_nueva;
  }

  get passwordNueva2() {
    return this.formulario.controls.password_nueva2;
  }

  faltantesPassword(): string[] {
    return this.passwordNueva.getError('fuerza')?.faltantes ?? [];
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.cargando.set(true);
    this.error.set(null);

    this.auth.cambiarPassword({
      password_actual: this.passwordActual.value,
      password_nueva: this.passwordNueva.value,
    }).subscribe({
      next: () => {
        this.cargando.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: (e: ErrorAuth) => {
        this.cargando.set(false);
        this.error.set(e);
      },
    });
  }
}
