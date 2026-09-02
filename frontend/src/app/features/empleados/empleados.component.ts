import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';
import { EmpleadosService } from '../../core/services/empleados.service';
import { AuthService } from '../../core/services/auth.service';
import { debounce, programarAviso } from '../../core/utils/temporizador.util';
import { DatosEmpleado, Empleado, ErrorEmpleado, RolAsignable } from '../../core/models/empleado.model';

const CERRAR_AVISO_MS = 4000;

@Component({
  selector: 'app-empleados',
  imports: [ReactiveFormsModule, PanelShellComponent],
  templateUrl: './empleados.component.html',
  styleUrl: './empleados.component.css',
})
export class EmpleadosComponent {
  private readonly fb = inject(FormBuilder);
  private readonly empleados = inject(EmpleadosService);
  private readonly destroyRef = inject(DestroyRef);
  readonly auth = inject(AuthService);

  readonly tiposDocumento = ['CC', 'CE', 'NIT', 'PAS'];

  readonly lista = signal<Empleado[]>([]);
  readonly roles = signal<RolAsignable[]>([]);
  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);
  readonly editando = signal<Empleado | null>(null);
  readonly formularioAbierto = signal(false);
  readonly busqueda = signal('');
  readonly filtroEstado = signal<'todos' | 'activos' | 'inactivos'>('activos');
  /** Contrasena temporal a mostrar una sola vez (RN-09), tras crear o
   * regenerar; se pierde al cerrar el aviso. */
  readonly passwordTemporal = signal<string | null>(null);
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  private readonly buscarDebounced = debounce(this.destroyRef, () => this.cargar(), 300);

  readonly formulario = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(120)]],
    email: ['', [Validators.required, Validators.email]],
    password: [''],
    rol: ['', Validators.required],
    tipo_documento: [''],
    numero_documento: [''],
    telefono: ['', [Validators.maxLength(20)]],
    cargo: ['', [Validators.maxLength(80)]],
    fecha_ingreso: [''],
  });

  ngOnInit(): void {
    this.cargar();
    this.cargarRoles();
  }

  cargar(): void {
    this.cargando.set(true);
    this.empleados.listar({ busqueda: this.busqueda(), estado: this.filtroEstado() }).subscribe({
      next: ({ resultados }) => {
        this.lista.set(resultados);
        this.cargando.set(false);
      },
      error: (e: ErrorEmpleado) => {
        this.error.set(e.detalle ?? 'No se pudo cargar la lista.');
        this.cargando.set(false);
      },
    });
  }

  cargarRoles(): void {
    this.empleados.listarRoles().subscribe(({ resultados }) => this.roles.set(resultados));
  }

  buscar(evento: Event): void {
    this.busqueda.set((evento.target as HTMLInputElement).value.trim());
    this.buscarDebounced();
  }

  filtrar(estado: 'todos' | 'activos' | 'inactivos'): void {
    this.filtroEstado.set(estado);
    this.cargar();
  }

  abrirCreacion(): void {
    this.editando.set(null);
    this.formulario.reset({
      nombre: '', email: '', password: '', rol: '', tipo_documento: '',
      numero_documento: '', telefono: '', cargo: '', fecha_ingreso: '',
    });
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  abrirEdicion(empleado: Empleado): void {
    this.editando.set(empleado);
    this.formulario.reset({
      nombre: empleado.nombre,
      email: empleado.email,
      password: '',
      rol: empleado.rol,
      tipo_documento: empleado.tipo_documento ?? '',
      numero_documento: empleado.numero_documento ?? '',
      telefono: empleado.telefono,
      cargo: empleado.cargo,
      fecha_ingreso: empleado.fecha_ingreso ?? '',
    });
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  cerrarFormulario(): void {
    this.formularioAbierto.set(false);
    this.editando.set(null);
    this.error.set(null);
  }

  enviar(): void {
    if (this.guardando()) return;
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const valores = this.formulario.getRawValue();
    const datos: Partial<DatosEmpleado> = {
      ...valores,
      tipo_documento: valores.tipo_documento || null,
      numero_documento: valores.numero_documento || null,
      fecha_ingreso: valores.fecha_ingreso || null,
    };
    if (!datos.password) delete datos.password;
    const enEdicion = this.editando();
    this.guardando.set(true);

    if (enEdicion) {
      this.empleados.editar(enEdicion.id, datos).subscribe({
        next: () => {
          this.guardando.set(false);
          this.exito.set('Empleado actualizado.');
          this.cerrarFormulario();
          this.cargar();
          this.avisarExito();
        },
        error: (e: ErrorEmpleado) => {
          this.guardando.set(false);
          this.error.set(e.detalle ?? 'Datos invalidos.');
        },
      });
      return;
    }

    this.empleados.crear(datos as DatosEmpleado).subscribe({
      next: (creado) => {
        this.guardando.set(false);
        this.exito.set('Empleado creado.');
        if (creado.password_temporal) this.passwordTemporal.set(creado.password_temporal);
        this.cerrarFormulario();
        this.cargar();
        this.avisarExito();
      },
      error: (e: ErrorEmpleado) => {
        this.guardando.set(false);
        this.error.set(e.detalle ?? 'Datos invalidos.');
      },
    });
  }

  /** Oculta el aviso de "exito" despues de unos segundos. */
  private avisarExito(): void {
    programarAviso(this.destroyRef, () => this.exito.set(null), CERRAR_AVISO_MS);
  }

  alternarActivo(empleado: Empleado): void {
    const accion = empleado.activo ? 'desactivar' : 'reactivar';
    this.empleados.cambiarEstado(empleado.id, accion).subscribe({
      next: (actualizado) => {
        this.lista.update((filas) =>
          filas.map((f) => (f.id === actualizado.id ? actualizado : f)));
        this.exito.set(actualizado.activo ? 'Empleado reactivado.' : 'Empleado desactivado.');
        this.avisarExito();
      },
      error: (e: ErrorEmpleado) => this.error.set(e.detalle ?? 'No se pudo cambiar el estado.'),
    });
  }

  regenerarPassword(empleado: Empleado): void {
    if (!confirm(`¿Generar una nueva contrasena temporal para ${empleado.nombre}?`)) return;
    this.empleados.regenerarPassword(empleado.id).subscribe({
      next: ({ password_temporal }) => this.passwordTemporal.set(password_temporal),
      error: (e: ErrorEmpleado) => this.error.set(e.detalle ?? 'No se pudo generar la contrasena.'),
    });
  }

  campoInvalido(nombre: string): boolean {
    const control = this.formulario.get(nombre);
    return !!control && control.invalid && control.touched;
  }
}
