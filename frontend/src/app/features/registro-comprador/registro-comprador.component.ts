import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthShellComponent } from '../../shared/layout/auth-shell/auth-shell.component';
import { ErrorAuth } from '../../core/models/auth.model';
import { AuthService } from '../../core/services/auth.service';
import { emailUnicoValidator } from '../../core/validators/email.validator';
import { fuerzaPassword, passwordsIguales } from '../../core/validators/password.validators';

const TIPOS_DOCUMENTO = [
  { valor: 'CC', etiqueta: 'Cedula de Ciudadania' },
  { valor: 'CE', etiqueta: 'Cedula de Extranjeria' },
  { valor: 'PAS', etiqueta: 'Pasaporte' },
  { valor: 'NIT', etiqueta: 'NIT' },
];

@Component({
  selector: 'app-registro-comprador',
  imports: [ReactiveFormsModule, RouterLink, AuthShellComponent],
  templateUrl: './registro-comprador.component.html',
  styleUrl: './registro-comprador.component.css',
})
export class RegistroCompradorComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly tiposDocumento = TIPOS_DOCUMENTO;

  readonly formulario = this.fb.nonNullable.group(
    {
      nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(120)]],
      email: ['', [Validators.required, Validators.email], [emailUnicoValidator(this.auth)]],
      password: ['', [Validators.required, fuerzaPassword]],
      password2: ['', [Validators.required]],
      tipo_documento: ['CC', [Validators.required]],
      numero_documento: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(20)]],
      telefono: ['', []],
      ciudad: ['', []],
    },
    { validators: passwordsIguales('password', 'password2') },
  );

  readonly cargando = signal(false);
  readonly error = signal<ErrorAuth | null>(null);
  readonly verPassword = signal(false);

  get c() {
    return this.formulario.controls;
  }

  faltantesPassword(): string[] {
    return this.c.password.getError('fuerza')?.faltantes ?? [];
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
      .registrarComprador({
        nombre: v.nombre,
        email: v.email,
        password: v.password,
        tipo_documento: v.tipo_documento,
        numero_documento: v.numero_documento,
        telefono: v.telefono ?? '',
        ciudad: v.ciudad ?? '',
      })
      .subscribe({
        next: () => {
          this.cargando.set(false);
          this.router.navigate(['/login'], { queryParams: { registrado: '1' } });
        },
        error: (e: ErrorAuth) => {
          this.cargando.set(false);
          this.error.set(e);
        },
      });
  }
}
