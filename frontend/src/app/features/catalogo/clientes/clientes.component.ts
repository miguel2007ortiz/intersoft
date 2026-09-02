import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { PanelShellComponent } from '../../../shared/layout/panel-shell/panel-shell.component';
import { AuthService } from '../../../core/services/auth.service';
import { CatalogoService } from '../../../core/services/catalogo.service';
import { SeguridadService } from '../../../core/services/seguridad.service';
import { debounce, programarAviso } from '../../../core/utils/temporizador.util';
import { ErrorCatalogo, Cliente } from '../../../core/models/catalogo.model';
import { UsuarioAdmin } from '../../../core/models/seguridad.model';

const TIPOS_DOCUMENTO = ['CC', 'NIT', 'CE', 'PAS'] as const;
const CERRAR_AVISO_MS = 4000;

@Component({
  selector: 'app-clientes',
  imports: [ReactiveFormsModule, PanelShellComponent],
  templateUrl: './clientes.component.html',
  styleUrl: './clientes.component.css',
})
export class ClientesComponent {
  private readonly fb = inject(FormBuilder);
  private readonly catalogo = inject(CatalogoService);
  private readonly seguridad = inject(SeguridadService);
  private readonly destroyRef = inject(DestroyRef);
  readonly auth = inject(AuthService);

  readonly tiposDocumento = TIPOS_DOCUMENTO;
  readonly clientes = signal<Cliente[]>([]);
  readonly usuarios = signal<UsuarioAdmin[]>([]);
  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);
  readonly exito = signal<string | null>(null);
  readonly editando = signal<Cliente | null>(null);
  readonly formularioAbierto = signal(false);
  readonly busqueda = signal('');
  readonly estado = signal<'activos' | 'inactivos' | 'todos'>('activos');
  readonly pagina = signal(1);
  readonly totalPaginas = signal(1);
  readonly total = signal(0);
  /** Agrupa las teclas del buscador: evita golpear la API en cada tecla. */
  private readonly buscarDebounced = debounce(this.destroyRef, () => this.cargar(), 300);

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
    this.catalogo.listarClientes({
      busqueda: this.busqueda(), estado: this.estado(), pagina: this.pagina(),
    }).subscribe({
      next: (r) => {
        this.clientes.set(r.resultados);
        this.total.set(r.total);
        this.totalPaginas.set(r.total_paginas ?? 1);
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
    this.pagina.set(1);
    this.buscarDebounced();
  }

  limpiarBusqueda(): void {
    this.busqueda.set('');
    this.pagina.set(1);
    this.cargar();
  }

  filtrarPorEstado(evento: Event): void {
    this.estado.set((evento.target as HTMLSelectElement).value as 'activos' | 'inactivos' | 'todos');
    this.pagina.set(1);
    this.cargar();
  }

  irPagina(nueva: number): void {
    if (nueva < 1 || nueva > this.totalPaginas()) return;
    this.pagina.set(nueva);
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
    if (this.guardando()) return;
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
    this.guardando.set(true);

    const peticion = enEdicion
      ? this.catalogo.editarCliente(enEdicion.id, datos)
      : this.catalogo.crearCliente(datos);

    peticion.subscribe({
      next: (cliente) => {
        this.guardando.set(false);
        this.exito.set(enEdicion ? 'Cliente actualizado.' : `Cliente ${cliente.nombre} creado.`);
        this.cerrarFormulario();
        this.cargar();
        this.avisarExito();
      },
      error: (e: ErrorCatalogo) => {
        this.guardando.set(false);
        this.error.set(e.detalle ?? 'Datos invalidos.');
      },
    });
  }

  /** Oculta el aviso de "exito" despues de unos segundos. */
  private avisarExito(): void {
    programarAviso(this.destroyRef, () => this.exito.set(null), CERRAR_AVISO_MS);
  }

  desactivar(cliente: Cliente): void {
    if (!confirm(`¿Desactivar a "${cliente.nombre}"? Dejara de aparecer en nuevas ventas, `
      + 'pero su historial se conserva y puedes reactivarlo cuando quieras.')) {
      return;
    }
    this.catalogo.cambiarEstadoCliente(cliente.id, 'desactivar').subscribe({
      next: () => {
        this.exito.set('Cliente desactivado.');
        this.cargar();
        this.avisarExito();
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'No se pudo desactivar.'),
    });
  }

  reactivar(cliente: Cliente): void {
    this.catalogo.cambiarEstadoCliente(cliente.id, 'reactivar').subscribe({
      next: () => {
        this.exito.set('Cliente reactivado.');
        this.cargar();
        this.avisarExito();
      },
      error: (e: ErrorCatalogo) => this.error.set(e.detalle ?? 'No se pudo reactivar.'),
    });
  }

  campoInvalido(nombre: string): boolean {
    const control = this.formulario.get(nombre);
    return !!control && control.invalid && control.touched;
  }
}
