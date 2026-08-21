import { Component } from '@angular/core';

@Component({
  selector: 'app-site-footer',
  template: `
    <footer class="pie">
      <div class="contenedor pie-int">
        <div class="marca">
          <span class="logo">Inter<span>Soft</span></span>
          <p>Tu mejor aliado en la gestion empresarial.</p>
        </div>
        <div>
          <h4>Contacto</h4>
          <p>soporte&#64;intersoft.co</p>
          <p>+57 300 123 4567</p>
        </div>
        <div>
          <h4>Siguenos</h4>
          <p class="redes">Facebook · Instagram · LinkedIn</p>
        </div>
      </div>
      <div class="contenedor derechos">
        <small>© 2026 InterSoft. Proyecto formativo SENA.</small>
      </div>
    </footer>
  `,
  styles: [
    `
      .pie {
        background: var(--oscuro);
        color: rgba(255, 255, 255, 0.72);
        padding: var(--e7) 0 var(--e5);
        font-size: 14.5px;
      }
      .pie-int {
        display: grid;
        gap: var(--e5);
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }
      .logo { font-size: 22px; font-weight: 700; color: #fff; text-decoration: none; }
      .logo span { color: #7ea2f5; }
      .marca p { margin: var(--e1) 0 0; max-width: 280px; }
      h4 { color: #fff; margin: 0 0 var(--e2); font-size: 15px; letter-spacing: 0.02em; }
      p { margin: 0 0 var(--e1); }
      .redes { color: rgba(255, 255, 255, 0.72); }

      .derechos {
        margin-top: var(--e5);
        padding-top: var(--e4);
        border-top: 1px solid rgba(255, 255, 255, 0.12);
        text-align: center;
        font-size: 13.5px;
        color: rgba(255, 255, 255, 0.55);
      }

      @media (max-width: 640px) {
        .pie-int { text-align: center; }
        .marca p { margin-inline: auto; }
      }
    `,
  ],
})
export class SiteFooterComponent {}
