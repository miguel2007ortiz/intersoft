import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Categoria, Cliente, DatosCliente, DatosProducto, ErrorCatalogo, Producto,
} from '../models/catalogo.model';

interface Lista<T> { resultados: T[]; total: number; }

@Injectable({ providedIn: 'root' })
export class CatalogoService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}`;

  // ---- Clientes ----
  listarClientes(busqueda = ''): Observable<Lista<Cliente>> {
    return this.http
      .get<Lista<Cliente>>(`${this.api}/clientes/`, { params: busqueda ? { busqueda } : {} })
      .pipe(capturarError<Lista<Cliente>>());
  }

  crearCliente(datos: DatosCliente): Observable<Cliente> {
    return this.http.post<Cliente>(`${this.api}/clientes/`, datos)
      .pipe(capturarError<Cliente>());
  }

  editarCliente(id: string, datos: Partial<DatosCliente>): Observable<Cliente> {
    return this.http.patch<Cliente>(`${this.api}/clientes/${id}/`, datos)
      .pipe(capturarError<Cliente>());
  }

  eliminarCliente(id: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/clientes/${id}/`)
      .pipe(capturarError<void>());
  }

  // ---- Productos ----
  listarProductos(opciones: { busqueda?: string; activo?: boolean } = {}):
    Observable<Lista<Producto>> {
      const params: Record<string, string> = {};
      if (opciones.busqueda) params['busqueda'] = opciones.busqueda;
      if (opciones.activo !== undefined) params['activo'] = String(opciones.activo);
      return this.http.get<Lista<Producto>>(`${this.api}/productos/`, { params })
        .pipe(capturarError<Lista<Producto>>());
  }

  crearProducto(datos: DatosProducto): Observable<Producto> {
    return this.http.post<Producto>(`${this.api}/productos/`, datos)
      .pipe(capturarError<Producto>());
  }

  editarProducto(id: string, datos: Partial<DatosProducto>): Observable<Producto> {
    return this.http.patch<Producto>(`${this.api}/productos/${id}/`, datos)
      .pipe(capturarError<Producto>());
  }

  cambiarEstadoProducto(id: string, accion: 'desactivar' | 'reactivar'): Observable<Producto> {
    return this.http.post<Producto>(`${this.api}/productos/${id}/${accion}/`, {})
      .pipe(capturarError<Producto>());
  }

  eliminarProducto(id: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/productos/${id}/`)
      .pipe(capturarError<void>());
  }

  // ---- Categorias ----
  listarCategorias(): Observable<Lista<Categoria>> {
    return this.http.get<Lista<Categoria>>(`${this.api}/categorias/`)
      .pipe(capturarError<Lista<Categoria>>());
  }

  crearCategoria(nombre: string): Observable<Categoria> {
    return this.http.post<Categoria>(`${this.api}/categorias/`, { nombre })
      .pipe(capturarError<Categoria>());
  }
}

/** Convierte la respuesta de error de Django en un mensaje legible. */
function capturarError<T>(): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) => throwError(() => traducir(e)));
}

function traducir(e: HttpErrorResponse): ErrorCatalogo {
  const cuerpo = (e.error ?? {}) as ErrorCatalogo;
  if (e.status === 0) return { detalle: 'No hay conexion con el servidor.' };
  if (e.status === 403) {
    return { detalle: 'Solo el personal de la empresa puede hacer esto.' };
  }
  if (cuerpo.errores) {
    const primerCampo = Object.values(cuerpo.errores)[0];
    const mensaje = Array.isArray(primerCampo) ? String(primerCampo[0]) : cuerpo.detalle;
    return { codigo: cuerpo.codigo, detalle: mensaje };
  }
  return { codigo: cuerpo.codigo, detalle: cuerpo.detalle ?? 'Ocurrio un error inesperado.' };
}
