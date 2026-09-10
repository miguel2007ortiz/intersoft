/**
 * Configuracion — datos de la empresa y preferencias de la cuenta
 *
 * Que hace: edita los datos de la empresa y del perfil, y cambia entre modo
 * claro y modo noche.
 * Ruta: /configuracion (authGuard).
 * Por que asi: el tema lo guarda TemaService en localStorage y se aplica al
 * <body>, por eso sobrevive a la recarga y afecta a toda la aplicacion, no
 * solo a esta pantalla.
 */

import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TemaService } from '../../core/services/tema.service';
import { PanelShellComponent } from '../../shared/layout/panel-shell/panel-shell.component';

@Component({
  selector: 'app-configuracion',
  imports: [PanelShellComponent, RouterLink],
  templateUrl: './configuracion.component.html',
  styleUrls: ['./configuracion.component.css'],
})
export class ConfiguracionComponent {
  readonly auth = inject(AuthService);
  readonly tema = inject(TemaService);
}
