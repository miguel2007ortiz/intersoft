import { DecimalPipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EstadoPago } from '../../../core/models/tienda.model';
import { TiendaService } from '../../../core/services/tienda.service';
import { CLAVE_REFERENCIA_PAGO } from '../../../core/utils/pasarela.util';

/** Intervalo entre consultas y tope de espera. El webhook suele llegar en
 * segundos, pero puede demorarse si la pasarela reintenta. */
const MS_ENTRE_CONSULTAS = 2500;
const MAX_CONSULTAS = 24; // ~60 s

@Component({
  selector: 'app-pago-retorno',
  imports: [DecimalPipe, RouterLink],
  template: `
    <div class="retorno">
      <h1>Resultado de tu pago</h1>

      @if (cargando()) {
        <div class="caja espera" role="status" aria-live="polite">
          <div class="giro" aria-hidden="true"></div>
          <h2>Confirmando tu pago</h2>
          <p>Estamos esperando la confirmacion de la pasarela. No cierres esta pagina.</p>
        </div>
      } @else if (error()) {
        <div class="caja fallo" role="alert">
          <h2>No pudimos consultar tu pago</h2>
          <p>{{ error() }}</p>
          <div class="acciones">
            <a routerLink="/pedidos" class="btn-principal">Ver mis pedidos</a>
          </div>
        </div>
      } @else if (estado(); as e) {
        @if (e.estado === 'aprobado') {
          <div class="caja exito" role="status">
            <div class="icono" aria-hidden="true">&#10003;</div>
            <h2>Pago aprobado</h2>
            <ul class="ventas">
              @for (v of e.ventas; track v.venta_id) {
                <li>
                  <strong>{{ v.empresa_nombre }}</strong>
                  <span>Factura {{ v.numero_factura }}</span>
                  <span class="total">{{ v.total | number }} COP</span>
                </li>
              }
            </ul>
            <p class="total-general">Total pagado: <strong>{{ e.total | number }} COP</strong></p>
            <p class="transaccion">Transaccion: {{ e.transaccion_id }}</p>
            <div class="acciones">
              <a routerLink="/catalogo" class="btn-principal">Seguir comprando</a>
              <a routerLink="/pedidos" class="btn-secundario">Ver mis pedidos</a>
            </div>
          </div>
        } @else if (e.estado === 'rechazado') {
          <div class="caja fallo" role="alert">
            <div class="icono" aria-hidden="true">&#10005;</div>
            <h2>Pago rechazado</h2>
            <p>
              La pasarela no aprobo el cobro. No se te cobro nada y tu carrito
              sigue intacto: puedes intentarlo con otro medio de pago.
            </p>
            <div class="acciones">
              <a routerLink="/checkout" class="btn-principal">Reintentar el pago</a>
              <a routerLink="/carrito" class="btn-secundario">Volver al carrito</a>
            </div>
          </div>
        } @else {
          <div class="caja espera" role="status" aria-live="polite">
            <h2>Tu pago sigue en proceso</h2>
            <p>
              La pasarela aun no confirma el cobro. Puede tardar unos minutos.
              Revisa tus pedidos mas tarde: si el pago se aprueba, la compra
              queda registrada automaticamente.
            </p>
            <div class="acciones">
              <button type="button" class="btn-principal" (click)="consultarAhora()">
                Consultar de nuevo
              </button>
              <a routerLink="/pedidos" class="btn-secundario">Ver mis pedidos</a>
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .retorno { max-width: 600px; margin: 0 auto; padding: var(--e5) var(--e4); }
    .retorno h1 { font-size: clamp(22px, 4vw, 28px); margin: 0 0 var(--e5); }

    .caja { border-radius: 12px; padding: 32px; text-align: center; }
    .caja h2 { margin: 0 0 var(--e3); }
    .caja p { margin: 4px 0; font-size: 15px; }

    .espera { background: var(--superficie); border: 1px solid var(--linea); color: var(--texto); }
    .exito { background: #ecfdf3; border: 1px solid #d1fadf; color: #067647; }
    .exito h2, .exito span { color: #067647; }
    .fallo { background: #fef3f2; border: 1px solid #fecdca; color: #b42318; }
    .fallo h2 { color: #b42318; }

    .icono {
      width: 60px; height: 60px; border-radius: 50%; color: #fff;
      font-size: 28px; font-weight: 700; display: flex;
      align-items: center; justify-content: center; margin: 0 auto var(--e3);
    }
    .exito .icono { background: #067647; }
    .fallo .icono { background: #b42318; }

    .giro {
      width: 40px; height: 40px; margin: 0 auto var(--e3);
      border: 3px solid var(--linea); border-top-color: var(--primario);
      border-radius: 50%; animation: girar 1s linear infinite;
    }
    @keyframes girar { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) {
      .giro { animation: none; border-top-color: var(--linea); }
    }

    .ventas {
      list-style: none; margin: 0 auto var(--e4); padding: 0;
      max-width: 360px; text-align: left; font-size: 14px;
    }
    .ventas li {
      display: flex; justify-content: space-between; align-items: center;
      gap: var(--e2); padding: 10px 0; border-bottom: 1px solid #d1fadf;
    }
    .ventas li:last-child { border-bottom: 0; }
    .ventas .total { font-weight: 700; }
    .total-general { font-size: 16px !important; margin-top: var(--e2) !important; }
    .transaccion { font-size: 13px; opacity: .8; margin-top: var(--e2) !important; }

    .acciones {
      margin-top: var(--e4); display: flex; gap: var(--e3);
      justify-content: center; flex-wrap: wrap;
    }
    .btn-principal, .btn-secundario {
      padding: 10px 20px; border-radius: 8px; text-decoration: none;
      font: inherit; font-weight: 600; font-size: 14px; cursor: pointer;
    }
    .btn-principal { background: var(--primario); color: #fff; border: 0; }
    .btn-secundario {
      border: 1px solid var(--linea); color: var(--texto);
      background: var(--superficie);
    }
  `],
})
export class PagoRetornoComponent implements OnInit, OnDestroy {
  private readonly tienda = inject(TiendaService);
  private readonly ruta = inject(ActivatedRoute);

  readonly estado = signal<EstadoPago | null>(null);
  readonly cargando = signal(true);
  readonly error = signal('');

  private referencia = '';
  private intentos = 0;
  private temporizador?: ReturnType<typeof setTimeout>;

  ngOnInit(): void {
    // La referencia viene del sessionStorage porque la pasarela solo devuelve
    // su propio id de transaccion en la URL de retorno. Se acepta tambien por
    // query param para poder volver a esta pagina desde un enlace.
    this.referencia =
      this.ruta.snapshot.queryParamMap.get('referencia') ??
      sessionStorage.getItem(CLAVE_REFERENCIA_PAGO) ??
      '';

    if (!this.referencia) {
      this.cargando.set(false);
      this.error.set('No encontramos la referencia de tu pago en este navegador.');
      return;
    }
    this.consultar();
  }

  ngOnDestroy(): void {
    clearTimeout(this.temporizador);
  }

  /** Reinicia la espera cuando el comprador pide reconsultar a mano. */
  consultarAhora(): void {
    this.intentos = 0;
    this.cargando.set(true);
    this.consultar();
  }

  private consultar(): void {
    this.intentos += 1;
    this.tienda.estadoPago(this.referencia).subscribe({
      next: (e) => {
        this.estado.set(e);
        if (e.estado !== 'pendiente') {
          // Resuelto: se limpia la referencia para que una visita posterior a
          // esta pagina no muestre el resultado de una compra vieja.
          sessionStorage.removeItem(CLAVE_REFERENCIA_PAGO);
          this.cargando.set(false);
          return;
        }
        if (this.intentos >= MAX_CONSULTAS) {
          // Se deja de consultar, pero el pago sigue su curso: el webhook
          // registrara la compra aunque el comprador cierre la pagina.
          this.cargando.set(false);
          return;
        }
        this.temporizador = setTimeout(() => this.consultar(), MS_ENTRE_CONSULTAS);
      },
      error: (e) => {
        this.cargando.set(false);
        this.error.set(e?.detalle || 'No pudimos consultar el estado de tu pago.');
      },
    });
  }
}
