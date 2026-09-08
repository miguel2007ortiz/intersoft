import { HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { capturarErrorDjango, ErrorDjango, TraduccionErrorDjango } from './django-error.util';

const traducir = async (
  e: HttpErrorResponse,
  config?: TraduccionErrorDjango<ErrorDjango>,
): Promise<ErrorDjango> =>
  new Promise((resolve) => {
    new Observable<never>((sub) => sub.error(e))
      .pipe(capturarErrorDjango<ErrorDjango>(config))
      .subscribe({ error: (err) => resolve(err as ErrorDjango) });
  });

describe('capturarErrorDjango', () => {
  it('traduce sin conexion (status 0) a SIN_CONEXION', async () => {
    const err = await traducir(new HttpErrorResponse({ status: 0, error: {} }));
    expect(err).toEqual({
      codigo: 'SIN_CONEXION',
      detalle: 'No hay conexion con el servidor.',
    });
  });

  it('usa el mensaje configurado para el status HTTP', async () => {
    const err = await traducir(new HttpErrorResponse({ status: 401, error: {} }), {
      mensajesPorStatus: { 401: 'Debes iniciar sesion.' },
    });
    expect(err).toEqual({ detalle: 'Debes iniciar sesion.' });
  });

  it('deja pasar codigo y detalle plano del cuerpo', async () => {
    const err = await traducir(
      new HttpErrorResponse({
        status: 400,
        error: { codigo: 'SIN_CLIENTE', detalle: 'Falta cliente.' },
      }),
    );
    expect(err.codigo).toBe('SIN_CLIENTE');
    expect(err.detalle).toBe('Falta cliente.');
  });

  it('extrae el primer mensaje del primer campo de errores', async () => {
    const err = await traducir(
      new HttpErrorResponse({
        status: 400,
        error: { errores: { campo: ['Primer error', 'Segundo'] } },
      }),
    );
    expect(err.detalle).toBe('Primer error');
  });

  it('usa detalle por defecto si el cuerpo no trae nada util', async () => {
    const err = await traducir(new HttpErrorResponse({ status: 500, error: {} }));
    expect(err.detalle).toBe('Ocurrio un error inesperado.');
  });

  it('no extrae mensaje de errores que es un arreglo plano', async () => {
    const err = await traducir(new HttpErrorResponse({ status: 400, error: { errores: ['a'] } }));
    expect(err.detalle).toBe('Ocurrio un error inesperado.');
  });

  it('llama a enriquecer con (error, cuerpo, base) y conserva el resultado', async () => {
    const enriquecer = vi.fn(
      (_e: HttpErrorResponse, _cuerpo: Record<string, unknown>, base: ErrorDjango) => ({
        ...base,
        extra: 42,
      }),
    );
    const err = await traducir(
      new HttpErrorResponse({ status: 400, error: { codigo: 'X', detalle: 'Y' } }),
      { enriquecer },
    );
    expect(enriquecer).toHaveBeenCalled();
    expect(err).toMatchObject({ codigo: 'X', detalle: 'Y', extra: 42 });
  });
});
