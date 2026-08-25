import { Component } from '@angular/core';

/** Pie minimo y compartido por toda la app: nombre, tagline y copyright.
 * Se retiraron telefono, correo y redes sociales porque eran datos de
 * ejemplo sin destino real (ver AUDITORIA.md, seccion 9.2). */
@Component({
  selector: 'app-site-footer',
  template: `
    <footer class="pie">
      <div class="contenedor pie-int">
        <span class="logo">Inter<span>Soft</span></span>
        <p class="lema">Tu mejor aliado en la gestion empresarial.</p>
        <p class="derechos">© 2026 InterSoft. Proyecto formativo SENA.</p>
      </div>
    </footer>
  `,
  styles: [
    `
      .pie {
        background: var(--oscuro);
        color: rgba(255, 255, 255, 0.72);
        padding: var(--e5) 0;
        font-size: 14px;
      }
      .pie-int {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: var(--e1);
        text-align: center;
      }
      .logo { font-size: 18px; font-weight: 700; color: #fff; }
      .logo span { color: #7ea2f5; }
      .lema { margin: 0; }
      .derechos { margin: var(--e1) 0 0; font-size: 12.5px; color: rgba(255, 255, 255, 0.55); }
    `,
  ],
})
export class SiteFooterComponent {}
