import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { PanelShellComponent } from '../../../shared/layout/panel-shell/panel-shell.component';
import { AuthService } from '../../../core/services/auth.service';
import { SeguridadService } from '../../../core/services/seguridad.service';
import { ErrorSeguridad, UsuarioAdmin } from '../../../core/models/seguridad.model';

@Component({
  selector: 'app-usuarios',
  imports: [ReactiveFormsModule, PanelShellComponent],
  templateUrl: './usuarios.component.html',
  styleUrl: './usuarios.component.css',
})
export class UsuariosComponent {
  private readonly fb = inject(FormBuilder);
  private readonly seguridad = inject(SeguridadService);
  readonly auth = inject(AuthService);

  readonly usuarios = signal<UsuarioAdmin[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);

  /** id del usuario en edicion; null = formulario de creacion */
  readonly editando = signal<UsuarioAdmin | null>(null);
  readonly formularioAbierto = signal(false);

  readonly roles = ['ADMINISTRADOR', 'EMPLEADO', 'CLIENTE'];

  readonly formulario = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(120)]],
    email: ['', [Validators.required, Validators.email]],
    rol: ['EMPLEADO', Validators.required],
    password: ['', [Validators.minLength(8)]],
  });

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.seguridad.listarUsuarios().subscribe({
      next: ({ resultados }) => {
        this.usuarios.set(resultados);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle ?? 'No se pudo cargar la lista.');
        this.cargando.set(false);
      },
    });
  }

  abrirCreacion(): void {
    this.editando.set(null);
    this.formulario.reset({ nombre: '', email: '', rol: 'EMPLEADO', password: '' });
    this.formulario.controls.password.setValidators([Validators.required, Validators.minLength(8)]);
    this.formulario.controls.password.updateValueAndValidity();
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  abrirEdicion(usuario: UsuarioAdmin): void {
    this.editando.set(usuario);
    this.formulario.reset({
      nombre: usuario.nombre, email: usuario.email,
      rol: usuario.rol, password: '',
    });
    // En edicion la contrasena es opcional (solo si se quiere cambiar)
    this.formulario.controls.password.setValidators([Validators.minLength(8)]);
    this.formulario.controls.password.updateValueAndValidity();
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  cerrarFormulario(): void {
    this.formularioAbierto.set(false);
    this.editando.set(null);
    this.error.set(null);
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const datos = this.formulario.getRawValue();
    const enEdicion = this.editando();

    const peticion = enEdicion
      ? this.seguridad.editarUsuario(enEdicion.id, datos)
      : this.seguridad.crearUsuario(datos);

    peticion.subscribe({
      next: () => {
        this.exito.set(enEdicion ? 'Usuario actualizado.' : 'Usuario creado.');
        this.cerrarFormulario();
        this.cargar();
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorSeguridad) => this.error.set(e.detalle ?? 'Datos invalidos.'),
    });
  }

  alternarActivo(usuario: UsuarioAdmin): void {
    const peticion = usuario.activo
      ? this.seguridad.desactivarUsuario(usuario.id)
      : this.seguridad.reactivarUsuario(usuario.id);

    peticion.subscribe({
      next: (actualizado) => {
        this.usuarios.update((lista) =>
          lista.map((u) => (u.id === actualizado.id ? actualizado : u)));
        this.exito.set(actualizado.activo ? 'Cuenta reactivada.' : 'Cuenta desactivada.');
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorSeguridad) => this.error.set(e.detalle ?? 'No se pudo cambiar el estado.'),
    });
  }

  campoInvalido(nombre: string): boolean {
    const control = this.formulario.get(nombre);
    return !!control && control.invalid && control.touched;
  }
}
