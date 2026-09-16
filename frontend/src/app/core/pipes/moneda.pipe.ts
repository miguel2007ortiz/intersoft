/**
 * MonedaPipe — formato unico de dinero en toda la app (BUG-22 QA)
 *
 * Que hace: formatea un numero como pesos colombianos con es-CO
 * (1.234.567 COP), el mismo locale que registra app.config.ts. Evita que
 * cada modulo use su propio `| number }} COP` y que algunos muestren el
 * numero sin indicar la moneda (Ventas/Inventario).
 * Donde se usa: cualquier cifra de dinero del panel y del marketplace.
 * Por que asi: un solo pipe compartido garantiza el mismo formato en
 * Productos, Dashboard, Ventas, Inventario, clientes y tienda.
 */

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'moneda' })
export class MonedaPipe implements PipeTransform {
  transform(valor: number | string | null | undefined): string {
    const cantidad = typeof valor === 'string' ? Number(valor) : (valor ?? 0);
    if (!Number.isFinite(cantidad)) return '—';
    return `${cantidad.toLocaleString('es-CO', { maximumFractionDigits: 0 })} COP`;
  }
}
