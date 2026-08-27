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
