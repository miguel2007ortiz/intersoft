import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const BASE = 'http://127.0.0.1:4200';
const OUT = path.resolve('..', 'figma-marketplace', 'capturas-admin');
const EMAIL = 'ana@elprogreso.co';
const PASSWORD = 'demo12345';

const PANTALLAS = [
  ['dashboard', '01-dashboard', 'Panel (dashboard)'],
  ['pos', '02-pos', 'Punto de Venta'],
  ['ventas', '03-ventas', 'Ventas'],
  ['envios', '04-envios', 'Envios'],
  ['clientes', '05-clientes', 'Clientes'],
  ['empleados', '06-empleados', 'Empleados'],
  ['productos', '07-productos', 'Productos'],
  ['inventario', '08-inventario', 'Inventario'],
  ['alertas', '09-alertas', 'Alertas'],
  ['facturacion', '10-facturacion', 'Facturacion DIAN'],
  ['ia', '11-asistente-ia', 'Asistente IA'],
  ['admin/usuarios', '12-usuarios', 'Usuarios (solo admin)'],
  ['admin/roles', '13-roles', 'Roles y permisos'],
  ['reportes', '14-reportes', 'Reportes'],
  ['monitoreo/camaras', '15-camaras', 'Camaras'],
  ['monitoreo/notificaciones', '16-notificaciones', 'Notificaciones'],
  ['configuracion', '17-configuracion', 'Configuracion'],
];

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('#email', EMAIL);
  await page.fill('input[formControlName="password"]', PASSWORD);
  await Promise.all([
    page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 15000 }),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForLoadState('networkidle');
}

async function shoot(page, label, nombre) {
  await page.goto(`${BASE}/${label}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUT, `${nombre}.png`), fullPage: true });
  console.log(`ok ${nombre}.png (${label})`);
}

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();

const ctxDesktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
const pageDesktop = await ctxDesktop.newPage();
await login(pageDesktop);
for (const [label, nombre] of PANTALLAS) {
  await shoot(pageDesktop, label, nombre);
}
await ctxDesktop.close();

const ctxMobile = await browser.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 1 });
const pageMobile = await ctxMobile.newPage();
await login(pageMobile);
await shoot(pageMobile, 'dashboard', 'm-dashboard');
await shoot(pageMobile, 'ventas', 'm-ventas');
await ctxMobile.close();

await browser.close();
console.log('FIN');