import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { personalGuard } from './core/guards/personal.guard';

export const routes: Routes = [
  {
    path: '',
    title: 'InterSoft',
    loadComponent: () => import('./features/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'login',
    title: 'Iniciar sesion — InterSoft',
    loadComponent: () => import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'registro',
    title: 'Crear cuenta — InterSoft',
    loadComponent: () => import('./features/registro/registro.component').then((m) => m.RegistroComponent),
  },
  {
    path: 'recuperar',
    title: 'Recuperar contraseña',
    loadComponent: () =>
      import('./features/auth/recuperar-password/recuperar-password.component').then(
        (m) => m.RecuperarPasswordComponent,
      ),
  },
  {
    path: 'restablecer',
    title: 'Nueva contraseña',
    loadComponent: () =>
      import('./features/auth/restablecer-password/restablecer-password.component').then(
        (m) => m.RestablecerPasswordComponent,
      ),
  },
  {
    path: 'dashboard',
    title: 'Panel — InterSoft',
    canActivate: [authGuard],
    loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'configuracion',
    title: 'Configuracion — InterSoft',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/configuracion/configuracion.component').then((m) => m.ConfiguracionComponent),
  },
  {
    path: 'clientes',
    title: 'Clientes — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () =>
      import('./features/catalogo/clientes/clientes.component').then((m) => m.ClientesComponent),
  },
  {
    path: 'productos',
    title: 'Productos — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () =>
      import('./features/catalogo/productos/productos.component').then((m) => m.ProductosComponent),
  },
  {
    path: 'admin/usuarios',
    title: 'Usuarios — InterSoft',
    canActivate: [authGuard, adminGuard],
    loadComponent: () =>
      import('./features/administracion/usuarios/usuarios.component').then((m) => m.UsuariosComponent),
  },
  {
    path: 'admin/roles',
    title: 'Roles y permisos — InterSoft',
    canActivate: [authGuard, adminGuard],
    loadComponent: () =>
      import('./features/administracion/roles/roles.component').then((m) => m.RolesComponent),
  },
  { path: '**', redirectTo: '' },
];
