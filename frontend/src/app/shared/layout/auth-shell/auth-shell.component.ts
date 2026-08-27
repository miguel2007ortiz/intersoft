import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BrilloCursorDirective } from '../../directives/brillo-cursor.directive';
import { SiteFooterComponent } from '../site-footer/site-footer.component';

@Component({
  selector: 'app-auth-shell',
  imports: [RouterLink, BrilloCursorDirective, SiteFooterComponent],
  templateUrl: './auth-shell.component.html',
  styleUrl: './auth-shell.component.css',
})
export class AuthShellComponent {}
