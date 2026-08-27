import { Directive, ElementRef, HostListener, inject } from '@angular/core';

/** Actualiza --brillo-x/--brillo-y con la posicion del cursor para un
 * resplandor radial que sigue el mouse (ver .hero::before en home.component.css). */
@Directive({
  selector: '[appBrilloCursor]',
})
export class BrilloCursorDirective {
  private readonly el = inject(ElementRef<HTMLElement>).nativeElement;

  @HostListener('mousemove', ['$event'])
  mover(evento: MouseEvent): void {
    const rect = this.el.getBoundingClientRect();
    const x = ((evento.clientX - rect.left) / rect.width) * 100;
    const y = ((evento.clientY - rect.top) / rect.height) * 100;
    this.el.style.setProperty('--brillo-x', `${x}%`);
    this.el.style.setProperty('--brillo-y', `${y}%`);
  }
}
