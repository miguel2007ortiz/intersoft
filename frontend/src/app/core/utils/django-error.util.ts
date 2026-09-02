import { HttpErrorResponse } from '@angular/common/http';
import { OperatorFunction, catchError, throwError } from 'rxjs';

/** Estructura base de un error traducido de Django. Todos los modelos
 * ErrorXxx del proyecto comparten esta forma ({codigo?, detalle?, errores?})
 * y, opcionalmente, campos extra segun el dominio. */
export interface ErrorDjango {
  codigo?: string;
  detalle?: string;
  errores?: Record<string, unknown> | string[];
}

/** Configuracion opcional por servicio: mensajes por codigo de estado y un
 * puente para que cada servicio anade sus campos extra al error final. */
export interface TraduccionErrorDjango<
  E extends ErrorDjango,
> {
  /** Mensaje por defecto segun el codigo de estado HTTP (0 = sin conexion). */
  mensajesPorStatus?: Record<number, string>;
  /** Permite a cada servicio enriquecer el error con campos propios
   * (p. ej. ia.conversacion o empleado_inactivo_id) antes de lanzarlo. */
  enriquecer?: (e: HttpErrorResponse, cuerpo: Record<string, unknown>, base: ErrorDjango) => E;
}

/** Unica fuente de verdad para traducir los errores de Django a un objeto
 * {codigo, detalle, errores} legible. Sustituye los 7 duplicados que habia
 * en analytics/monitoreo/ia/empleados/catalogo/seguridad/tienda. */
export function capturarErrorDjango<T, E extends ErrorDjango = ErrorDjango>(
  config: TraduccionErrorDjango<E> = {},
): OperatorFunction<T, T> {
  return catchError((e: HttpErrorResponse) =>
    throwError(() => traducirDjango(e, config)),
  );
}

function traducirDjango<E extends ErrorDjango>(
  e: HttpErrorResponse,
  config: TraduccionErrorDjango<E>,
): E {
  const cuerpo = (e.error ?? {}) as Record<string, unknown>;

  if (e.status === 0) {
    const base: ErrorDjango = { codigo: 'SIN_CONEXION', detalle: 'No hay conexion con el servidor.' };
    return config.enriquecer
      ? config.enriquecer(e, cuerpo, base)
      : (base as E);
  }

  const mensajeStatus = config.mensajesPorStatus?.[e.status];
  if (mensajeStatus) {
    const base: ErrorDjango = { detalle: mensajeStatus };
    return config.enriquecer
      ? config.enriquecer(e, cuerpo, base)
      : (base as E);
  }

  const base: ErrorDjango = {
    codigo: typeof cuerpo['codigo'] === 'string' ? cuerpo['codigo'] : undefined,
    detalle: extraerDetalle(cuerpo) ?? 'Ocurrio un error inesperado.',
    errores: (cuerpo['errores'] as ErrorDjango['errores']) ?? undefined,
  };
  return config.enriquecer
    ? config.enriquecer(e, cuerpo, base)
    : (base as E);
}

/** Si Django devuelve {errores: {campo: [msg,...]}}, muestra el primer
 * mensaje del primer campo; si no, usa el detalle plano. */
function extraerDetalle(cuerpo: Record<string, unknown>): string | undefined {
  const errores = cuerpo['errores'] as Record<string, unknown> | undefined;
  if (errores && typeof errores === 'object' && !Array.isArray(errores)) {
    const primerCampo = Object.values(errores)[0];
    if (Array.isArray(primerCampo)) return String(primerCampo[0]);
  }
  return typeof cuerpo['detalle'] === 'string' ? cuerpo['detalle'] : undefined;
}
