import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthShellComponent } from '../../shared/layout/auth-shell/auth-shell.component';
import { ErrorAuth } from '../../core/models/auth.model';
import { AuthService } from '../../core/services/auth.service';
import { emailUnicoValidator } from '../../core/validators/email.validator';
import { fuerzaPassword, passwordsIguales } from '../../core/validators/password.validators';

@Component({
  selector: 'app-registro',
  imports: [ReactiveFormsModule, RouterLink, AuthShellComponent],
  templateUrl: './registro.component.html',
  styleUrl: './registro.component.css',
})
export class RegistroComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** La forma del formulario copia exactamente el JSON que espera Django. */
  readonly formulario = this.fb.nonNullable.group({
    empresa: this.fb.nonNullable.group({
      nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(150)]],
      nit: ['', [Validators.required, Validators.pattern(/^\d{9}$/)]],
    }),
    administrador: this.fb.nonNullable.group(
      {
        nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(120)]],
        email: ['', [Validators.required, Validators.email], [emailUnicoValidator(this.auth)]],
        password: ['', [Validators.required, fuerzaPassword]],
        password2: ['', [Validators.required]],
      },
      { validators: passwordsIguales('password', 'password2') },
    ),
  });

  readonly cargando = signal(false);
  readonly error = signal<ErrorAuth | null>(null);
  readonly verPassword = signal(false);

  get empresa() {
    return this.formulario.controls.empresa.controls;
  }

  get admin() {
    return this.formulario.controls.administrador.controls;
  }

  get grupoAdmin() {
    return this.formulario.controls.administrador;
  }

  faltantesPassword(): string[] {
    return this.admin.password.getError('fuerza')?.faltantes ?? [];
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.cargando.set(true);
    this.error.set(null);

    const v = this.formulario.getRawValue();
    this.auth
      .registrarEmpresa({
        empresa: { nombre: v.empresa.nombre, nit: v.empresa.nit },
        administrador: {
          nombre: v.administrador.nombre,
          email: v.administrador.email,
          password: v.administrador.password,
        },
      })
      .subscribe({
        next: () => {
          this.cargando.set(false);
          // No inicia sesion: manda al login con el aviso de cuenta creada.
          this.router.navigate(['/login'], { queryParams: { registrado: '1' } });
        },
        error: (e: ErrorAuth) => {
          this.cargando.set(false);
          this.error.set(e);
        },
      });
  }
}
