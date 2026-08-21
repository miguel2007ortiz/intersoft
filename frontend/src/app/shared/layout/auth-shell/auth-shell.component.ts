import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BrilloCursorDirective } from '../../directives/brillo-cursor.directive';

@Component({
  selector: 'app-auth-shell',
  imports: [RouterLink, BrilloCursorDirective],
  templateUrl: './auth-shell.component.html',
  styleUrl: './auth-shell.component.css',
})
export class AuthShellComponent {}
