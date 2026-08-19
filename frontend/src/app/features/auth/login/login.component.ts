import { Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthShellComponent } from '../../../shared/layout/auth-shell/auth-shell.component';
import { ErrorAuth } from '../../../core/models/auth.model';
import { AuthService } from '../../../core/services/auth.service';
import { WelcomeService } from '../../../core/services/welcome.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink, AuthShellComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent implements OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly welcome = inject(WelcomeService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  readonly formulario = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  readonly cargando = signal(false);
  readonly error = signal<ErrorAuth | null>(null);
  readonly verPassword = signal(false);

  /** Avisos que llegan por query param desde otras pantallas. */
  readonly recienRegistrado = this.ruta.snapshot.queryParamMap.get('registrado') === '1';
  readonly sesionExpirada = this.ruta.snapshot.queryParamMap.get('expirada') === '1';

  /** Reloj de 1s: alimenta la cuenta regresiva del bloqueo. */
  private readonly ahora = signal(Date.now());
  private readonly reloj = setInterval(() => this.ahora.set(Date.now()), 1000);

  readonly segundosBloqueo = computed(() => {
    const desbloqueo = this.error()?.desbloqueoEn;
    if (!desbloqueo) return 0;
    const restante = Math.ceil((new Date(desbloqueo).getTime() - this.ahora()) / 1000);
    return restante > 0 ? restante : 0;
  });

  readonly cuentaRegresiva = computed(() => {
    const total = this.segundosBloqueo();
    const min = Math.floor(total / 60);
    const seg = total % 60;
    return `${min}:${seg.toString().padStart(2, '0')}`;
  });

  get email() {
    return this.formulario.controls.email;
  }

  get password() {
    return this.formulario.controls.password;
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.cargando.set(true);

    this.auth.login(this.formulario.getRawValue()).subscribe({
      next: () => {
        this.cargando.set(false);
        const nombre = this.auth.usuario()?.nombre;
        if (nombre) this.welcome.mostrar(nombre);
        const destino = this.ruta.snapshot.queryParamMap.get('redirigir') ?? '/dashboard';
        this.router.navigateByUrl(destino);
      },
      error: (e: ErrorAuth) => {
        this.cargando.set(false);
        this.error.set(e);
        this.password.reset();
      },
    });
  }

  ngOnDestroy(): void {
    clearInterval(this.reloj);
  }
}
