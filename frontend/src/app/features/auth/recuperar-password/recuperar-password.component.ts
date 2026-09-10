/**
 * Recuperar contrasena — paso 1 de 2
 *
 * Que hace: pide el correo y dispara el envio del enlace de restablecimiento.
 * Ruta: /recuperar (publica).
 * Por que asi: la respuesta es siempre la misma haya o no cuenta con ese
 * correo. Es a proposito: si dijera "ese correo no existe" cualquiera podria
 * averiguar que cuentas hay registradas.
 */

import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthShellComponent } from '../../../shared/layout/auth-shell/auth-shell.component';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-recuperar-password',
  imports: [ReactiveFormsModule, RouterLink, AuthShellComponent],
  templateUrl: './recuperar-password.component.html',
  styleUrl: './recuperar-password.component.css',
})
export class RecuperarPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);

  readonly formulario = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  readonly cargando = signal(false);
  readonly enviado = signal(false);

  get email() {
    return this.formulario.controls.email;
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.cargando.set(true);

    // Mismo principio de seguridad que el backend: exista o no la cuenta,
    // el mensaje que ve el usuario es identico (no revela quien esta registrado).
    this.auth.solicitarRecuperacion(this.email.value).subscribe({
      next: () => {
        this.cargando.set(false);
        this.enviado.set(true);
      },
      error: () => {
        this.cargando.set(false);
        this.enviado.set(true);
      },
    });
  }
}
