import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { personalGuard } from './core/guards/personal.guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Marketplace — InterSoft',
    loadComponent: () =>
      import('./features/tienda/catalogo/catalogo.component').then((m) => m.CatalogoComponent),
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
    path: 'registro-comprador',
    title: 'Crear cuenta de comprador — InterSoft',
    loadComponent: () =>
      import('./features/registro-comprador/registro-comprador.component').then(
        (m) => m.RegistroCompradorComponent,
      ),
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
  {
    path: 'pos',
    title: 'Punto de Venta — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () => import('./features/pos/pos.component').then((m) => m.PosComponent),
  },
  {
    path: 'reportes',
    title: 'Reportes — InterSoft',
    canActivate: [authGuard, adminGuard],
    loadComponent: () =>
      import('./features/reportes/reportes.component').then((m) => m.ReportesComponent),
  },
  {
    path: 'ventas',
    title: 'Ventas — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () => import('./features/ventas/ventas.component').then((m) => m.VentasComponent),
  },
  {
    path: 'inventario',
    title: 'Inventario — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () =>
      import('./features/inventario/inventario.component').then((m) => m.InventarioComponent),
  },
  {
    path: 'alertas',
    title: 'Alertas — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () => import('./features/alertas/alertas.component').then((m) => m.AlertasComponent),
  },
  {
    path: 'catalogo',
    title: 'Tienda — InterSoft',
    loadComponent: () =>
      import('./features/tienda/catalogo/catalogo.component').then((m) => m.CatalogoComponent),
  },
  {
    path: 'carrito',
    title: 'Carrito — InterSoft',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/tienda/carrito/carrito.component').then((m) => m.CarritoComponent),
  },
  {
    path: 'checkout',
    title: 'Checkout — InterSoft',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/tienda/checkout/checkout.component').then((m) => m.CheckoutComponent),
  },
  {
    path: 'pedidos',
    title: 'Mis pedidos — InterSoft',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/tienda/pedidos/pedidos.component').then((m) => m.PedidosComponent),
  },
  {
    path: 'facturacion',
    title: 'Facturacion DIAN — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () =>
      import('./features/facturacion/facturacion.component').then((m) => m.FacturacionComponent),
  },
  {
    path: 'ia',
    title: 'Asistente IA — InterSoft',
    canActivate: [authGuard, personalGuard],
    loadComponent: () => import('./features/ia/ia.component').then((m) => m.IaComponent),
  },
  {
    path: 'monitoreo/camaras',
    title: 'Camaras — InterSoft',
    canActivate: [authGuard, adminGuard],
    loadComponent: () =>
      import('./features/camaras/camaras.component').then((m) => m.CamarasComponent),
  },
  {
    path: 'monitoreo/notificaciones',
    title: 'Notificaciones — InterSoft',
    canActivate: [authGuard, adminGuard],
    loadComponent: () =>
      import('./features/notificaciones/notificaciones.component').then((m) => m.NotificacionesComponent),
  },
  { path: '**', redirectTo: '' },
];
