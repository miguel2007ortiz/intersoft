import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { PanelShellComponent } from '../../../shared/layout/panel-shell/panel-shell.component';
import { SeguridadService } from '../../../core/services/seguridad.service';
import {
  ErrorSeguridad, PermisoCatalogo, RolAdmin,
} from '../../../core/models/seguridad.model';

@Component({
  selector: 'app-roles',
  imports: [ReactiveFormsModule, PanelShellComponent],
  templateUrl: './roles.component.html',
  styleUrl: './roles.component.css',
})
export class RolesComponent {
  private readonly fb = inject(FormBuilder);
  private readonly seguridad = inject(SeguridadService);

  readonly roles = signal<RolAdmin[]>([]);
  readonly permisosCatalogo = signal<PermisoCatalogo[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);

  readonly editando = signal<RolAdmin | null>(null);
  readonly formularioAbierto = signal(false);
  /** id del rol desplegado en el acordeon (uno a la vez) */
  readonly expandido = signal<string | null>(null);

  /** codigos de permisos marcados en el formulario */
  readonly seleccionados = signal<Set<string>>(new Set());

  readonly formulario = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(30)]],
    descripcion: ['', [Validators.maxLength(200)]],
  });

  readonly haySeleccionados = computed(() => this.seleccionados().size > 0);

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.seguridad.listarRoles().subscribe({
      next: ({ resultados }) => {
        this.roles.set(resultados);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle ?? 'No se pudo cargar la lista de roles.');
        this.cargando.set(false);
      },
    });
    this.seguridad.listarPermisos().subscribe({
      next: ({ resultados }) => this.permisosCatalogo.set(resultados),
    });
  }

  abrirCreacion(): void {
    this.editando.set(null);
    this.formulario.reset({ nombre: '', descripcion: '' });
    this.seleccionados.set(new Set());
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  alternarAcordeon(id: string): void {
    this.expandido.update((actual) => (actual === id ? null : id));
  }

  abrirEdicion(rol: RolAdmin): void {
    this.editando.set(rol);
    this.formulario.reset({ nombre: rol.nombre, descripcion: rol.descripcion });
    this.seleccionados.set(new Set(rol.permisos));
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  cerrarFormulario(): void {
    this.formularioAbierto.set(false);
    this.editando.set(null);
    this.error.set(null);
  }

  alternarPermiso(codigo: string): void {
    this.seleccionados.update((actuales) => {
      const copia = new Set(actuales);
      if (copia.has(codigo)) {
        copia.delete(codigo);
      } else {
        copia.add(codigo);
      }
      return copia;
    });
  }

  enviar(): void {
    if (this.formulario.invalid || !this.haySeleccionados()) {
      this.formulario.markAllAsTouched();
      return;
    }
    const datos = {
      ...this.formulario.getRawValue(),
      permisos: [...this.seleccionados()],
    };
    const enEdicion = this.editando();

    const peticion = enEdicion
      ? this.seguridad.editarRol(enEdicion.id, datos)
      : this.seguridad.crearRol(datos);

    peticion.subscribe({
      next: () => {
        this.exito.set(enEdicion ? 'Rol actualizado.' : 'Rol creado.');
        this.cerrarFormulario();
        this.cargar();
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorSeguridad) => this.error.set(e.detalle ?? 'Datos invalidos.'),
    });
  }

  clonar(rol: RolAdmin): void {
    this.seguridad.clonarRol(rol.id).subscribe({
      next: (clon) => {
        this.exito.set(`Rol clonado como "${clon.nombre}". Ajusta su nombre y permisos.`);
        this.cargar();
        setTimeout(() => this.exito.set(null), 5000);
      },
      error: (e: ErrorSeguridad) => this.error.set(e.detalle ?? 'No se pudo clonar.'),
    });
  }

  eliminar(rol: RolAdmin): void {
    if (!confirm(`¿Eliminar el rol "${rol.nombre}"? Esta accion no se puede deshacer.`)) {
      return;
    }
    this.seguridad.eliminarRol(rol.id).subscribe({
      next: () => {
        this.exito.set('Rol eliminado.');
        this.cargar();
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorSeguridad) => this.error.set(e.detalle ?? 'No se pudo eliminar el rol.'),
    });
  }

  campoInvalido(nombre: string): boolean {
    const control = this.formulario.get(nombre);
    return !!control && control.invalid && control.touched;
  }
}
