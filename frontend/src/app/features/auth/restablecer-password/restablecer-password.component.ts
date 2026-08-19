import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthShellComponent } from '../../../shared/layout/auth-shell/auth-shell.component';
import { ErrorAuth } from '../../../core/models/auth.model';
import { AuthService } from '../../../core/services/auth.service';
import { fuerzaPassword, passwordsIguales } from '../../../core/validators/password.validators';

@Component({
  selector: 'app-restablecer-password',
  imports: [ReactiveFormsModule, RouterLink, AuthShellComponent],
  templateUrl: './restablecer-password.component.html',
  styleUrl: './restablecer-password.component.css',
})
export class RestablecerPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  /** El token llega por query param: /restablecer?token=... */
  readonly token = this.ruta.snapshot.queryParamMap.get('token') ?? '';

  readonly formulario = this.fb.nonNullable.group(
    {
      password: ['', [Validators.required, fuerzaPassword]],
      password2: ['', [Validators.required]],
    },
    { validators: passwordsIguales('password', 'password2') },
  );

  readonly cargando = signal(false);
  readonly error = signal<ErrorAuth | null>(null);
  readonly tokenInvalido = signal(false);
  readonly verPassword = signal(false);

  get password() {
    return this.formulario.controls.password;
  }

  get password2() {
    return this.formulario.controls.password2;
  }

  faltantesPassword(): string[] {
    return this.password.getError('fuerza')?.faltantes ?? [];
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.cargando.set(true);
    this.error.set(null);

    this.auth.restablecerPassword(this.token, this.password.value).subscribe({
      next: () => {
        this.cargando.set(false);
        this.router.navigate(['/login'], { queryParams: { registrado: '1' } });
      },
      error: (e: ErrorAuth) => {
        this.cargando.set(false);
        // El backend responde 400 tanto para token vencido/usado como para
        // contraseña debil; distinguimos por el detalle que envia.
        if (e.mensaje?.toLowerCase().includes('enlace')) {
          this.tokenInvalido.set(true);
        } else {
          this.error.set(e);
        }
      },
    });
  }
}
