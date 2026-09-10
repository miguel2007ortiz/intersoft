import { DestroyRef } from '@angular/core';
import { debounce, programarAviso } from './temporizador.util';

const destroyRefFalso = (): { destroyRef: DestroyRef; destruir: () => void } => {
  const onDestroy = vi.fn();
  const manejadores: (() => void)[] = [];
  const destroyRef = {
    onDestroy: vi.fn((fn: () => void) => {
      onDestroy(fn);
      manejadores.push(fn);
    }),
  } as unknown as DestroyRef;
  return {
    destroyRef,
    destruir: () => manejadores.forEach((fn) => fn()),
  };
};

describe('programarAviso', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('ejecuta el callback tras el retardo', () => {
    const ctx = destroyRefFalso();
    const fn = vi.fn();
    programarAviso(ctx.destroyRef, fn, 3000);
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(3000);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('registra la limpieza y cancela el timer al destruirse', () => {
    const ctx = destroyRefFalso();
    const fn = vi.fn();
    programarAviso(ctx.destroyRef, fn, 5000);
    ctx.destruir();
    vi.advanceTimersByTime(10000);
    expect(fn).not.toHaveBeenCalled();
  });
});

describe('debounce', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('dispara una sola vez tras la ultima llamada rapida', () => {
    const ctx = destroyRefFalso();
    const fn = vi.fn();
    const disparar = debounce(ctx.destroyRef, fn, 300);
    disparar();
    disparar();
    disparar();
    vi.advanceTimersByTime(299);
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('se cancela al destruirse el contenedor', () => {
    const ctx = destroyRefFalso();
    const fn = vi.fn();
    const disparar = debounce(ctx.destroyRef, fn, 300);
    disparar();
    ctx.destruir();
    vi.advanceTimersByTime(1000);
    expect(fn).not.toHaveBeenCalled();
  });
});
