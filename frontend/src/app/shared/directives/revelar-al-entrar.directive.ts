/**
 * revelarAlEntrar — anima un elemento cuando entra en pantalla
 *
 * Que hace: con IntersectionObserver, le pone la clase `.aparecer` al elemento
 * la primera vez que se ve, y deja de observarlo.
 * Donde se usa: secciones largas del marketplace y del dashboard.
 * Por que asi: IntersectionObserver lo resuelve el navegador; escuchar el
 * evento scroll obligaria a calcular posiciones en cada pixel movido. Se deja
 * de observar tras la primera vez para que el contenido no vuelva a
 * desvanecerse al subir.
 */

import { AfterViewInit, Directive, ElementRef, OnDestroy, inject } from '@angular/core';

/** Agrega .revelada cuando el elemento entra en el viewport (ver .por-revelar en styles.css). */
@Directive({
  selector: '[appRevelarAlEntrar]',
})
export class RevelarAlEntrarDirective implements AfterViewInit, OnDestroy {
  private readonly el = inject(ElementRef<HTMLElement>).nativeElement;
  private observador?: IntersectionObserver;

  ngAfterViewInit(): void {
    this.el.classList.add('por-revelar');
    this.observador = new IntersectionObserver(
      ([entrada]) => {
        if (entrada.isIntersecting) {
          this.el.classList.add('revelada');
          this.observador?.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    this.observador.observe(this.el);
  }

  ngOnDestroy(): void {
    this.observador?.disconnect();
  }
}
