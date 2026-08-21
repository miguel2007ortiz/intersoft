import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PanelShellComponent } from '../../../shared/layout/panel-shell/panel-shell.component';
import { AuthService } from '../../../core/services/auth.service';
import { CatalogoService } from '../../../core/services/catalogo.service';
import { SeguridadService } from '../../../core/services/seguridad.service';
import { ErrorCatalogo, Cliente } from '../../../core/models/catalogo.model';
import { UsuarioAdmin } from '../../../core/models/seguridad.model';

const TIPOS_DOCUMENTO = ['CC', 'NIT', 'CE', 'PAS'] as const;

@Component({
  selector: 'app-clientes',
  imports: [ReactiveFormsModule, RouterLink, PanelShellComponent],
  templateUrl: './clientes.component.html',
  styleUrl: './clientes.component.css',
})
export class ClientesComponent {
  private readonly fb = inject(FormBuilder);
  private readonly catalogo = inject(CatalogoService);
  private readonly seguridad = inject(SeguridadService);
  readonly auth = inject(AuthService);

  readonly tiposDocumento = TIPOS_DOCUMENTO;
  readonly clientes = signal<Cliente[]>([]);
  readonly usuarios = signal<UsuarioAdmin[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);
  readonly editando = signal<Cliente | null>(null);
  readonly formularioAbierto = signal(false);
  readonly busqueda = signal('');

  /** Solo el ADMINISTRADOR ve la lista de cuentas para vincular
   * (la API de seguridad es exclusiva de ese rol). */
  readonly puedeVincularUsuarios = this.auth.esAdministrador;

  readonly formulario = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(120)]],
    tipo_documento: ['CC', Validators.required],
    numero_documento: ['', [Validators.required, Validators.maxLength(20)]],
    email: ['', [Validators.email]],
    telefono: ['', [Validators.maxLength(20)]],
    ciudad: ['', [Validators.maxLength(80)]],
    usuario_id: [''],
  });

  readonly hayBusqueda = computed(() => this.busqueda().length > 0);

  ngOnInit(): void {
    this.cargar();
    if (this.puedeVincularUsuarios()) {
      this.seguridad.listarUsuarios()
        .subscribe(({ resultados }) => this.usuarios.set(resultados));
    }
  }

  cargar(): void {
    this.cargando.set(true);
    this.catalogo.listarClientes(this.busqueda()).subscribe({
      next: ({ resultados }) => {
        this.clientes.set(resultados);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e.detalle ?? 'No se pudo cargar la lista.');
        this.cargando.set(false);
      },
    });
  }

  buscar(evento: Event): void {
    this.busqueda.set((evento.target as HTMLInputElement).value.trim());
    this.cargar();
  }

  abrirCreacion(): void {
    this.editando.set(null);
    this.formulario.reset({
      nombre: '', tipo_documento: 'CC', numero_documento: '',
      email: '', telefono: '', ciudad: '', usuario_id: '',
    });
    this.error.set(null);
    this.formularioAbierto.set(true);
  }

  abrirEdicion(cliente: Cliente): void {
    this.editando.set(cliente);
    this.formulario.reset({
      nombre: cliente.nombre,
      tipo_documento: cliente.tipo_documento,
      numero_documento: cliente.numero_documento,
      email: cliente.email,
      telefono: cliente.telefono,
      ciudad: cliente.ciudad,
      usuario_id: cliente.usuario_id ?? '',
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
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const valores = this.formulario.getRawValue();
    const datos = {
      ...valores,
      usuario_id: valores.usuario_id || null,
    };
    const enEdicion = this.editando();

    const peticion = enEdicion
      ? this.catalogo.editarCliente(enEdicion.id, datos)
      : this.catalogo.crearCliente(datos);

    peticion.subscribe({
      next: (cliente) => {
        this.exito.set(enEdicion ? 'Cliente actualizado.' : `Cliente ${cliente.nombre} creado.`);
        this.cerrarFormulario();
        this.cargar();
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'Datos invalidos.'),
    });
  }

  eliminar(cliente: Cliente): void {
    if (!confirm(`¿Eliminar el cliente "${cliente.nombre}"? Su historial se conserva.`)) {
      return;
    }
    this.catalogo.eliminarCliente(cliente.id).subscribe({
      next: () => {
        this.exito.set('Cliente eliminado.');
        this.cargar();
        setTimeout(() => this.exito.set(null), 4000);
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'No se pudo eliminar.'),
    });
  }

  campoInvalido(nombre: string): boolean {
    const control = this.formulario.get(nombre);
    return !!control && control.invalid && control.touched;
  }
}
