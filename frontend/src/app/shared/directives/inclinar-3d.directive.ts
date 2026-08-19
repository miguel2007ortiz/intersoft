import { Directive, ElementRef, HostListener, Renderer2, inject } from '@angular/core';

/** Inclina la tarjeta en 3D siguiendo el cursor (efecto "tilt"). */
@Directive({
  selector: '[appInclinar3d]',
})
export class Inclinar3dDirective {
  private readonly el = inject(ElementRef<HTMLElement>).nativeElement;
  private readonly renderer = inject(Renderer2);
  private readonly maxGrados = 6;
  private readonly prefiereMenosMovimiento =
    typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  @HostListener('mousemove', ['$event'])
  mover(evento: MouseEvent): void {
    if (this.prefiereMenosMovimiento) return;
    const rect = this.el.getBoundingClientRect();
    const px = (evento.clientX - rect.left) / rect.width - 0.5;
    const py = (evento.clientY - rect.top) / rect.height - 0.5;
    const rotY = px * this.maxGrados * 2;
    const rotX = py * -this.maxGrados * 2;
    this.renderer.setStyle(
      this.el,
      'transform',
      `perspective(700px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateY(-4px)`,
    );
  }

  @HostListener('mouseleave')
  salir(): void {
    this.renderer.removeStyle(this.el, 'transform');
  }
}
