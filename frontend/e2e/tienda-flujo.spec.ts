import { expect, request, test } from '@playwright/test';

/**
 * Happy path del marketplace con el modulo de Envios (seccion 6 de AGENTS.md).
 * Requiere backend en 127.0.0.1:8000 con BD `intersoft1_db` migrada y
 * seed_demo aplicado. Usa la usuaria demo del seed (ana@elprogreso.co /
 * demo12345); en la BD demo es ADMINISTRADOR con cliente de marketplace y
 * direccion de envio, y un carrito pre-cargado.
 *
 * Determinismo: antes de correr, el beforeAll garantiza por API que el
 * carrito de Ana tenga al menos un item (una corrida previa puede haber
 * vaciado el carrito al hacer checkout).
 */

const API = process.env.API_URL ?? 'http://127.0.0.1:8000/api';
const USUARIO = { email: 'ana@elprogreso.co', pass: 'demo12345' };

/** Loguea en la UI y espera a que el navegador guarde la sesion (evita la
 * carrera entre el click del login y la redireccion a la ruta objetivo). */
async function cargarSesion(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/login');
  await page.locator('#email').fill(USUARIO.email);
  await page.locator('#password').fill(USUARIO.pass);
  await page.getByRole('button', { name: 'Iniciar sesion' }).click();
  await page.waitForFunction(() => window.localStorage.getItem('intersoft.token') !== null, null, {
    timeout: 20_000,
  });
}

async function tokenComprador(): Promise<string> {
  const ctx = await request.newContext();
  const r = await ctx.post(`${API}/auth/login/`, {
    data: { email: USUARIO.email, password: USUARIO.pass },
  });
  return (await r.json()).access as string;
}

test.beforeAll(async () => {
  const access = await tokenComprador();
  const ctx = await request.newContext({
    extraHTTPHeaders: { Authorization: `Bearer ${access}` },
  });
  const carrito = await (await ctx.get(`${API}/tienda/carrito/`)).json();
  if (!carrito.items?.length) {
    const catalogo = await (await ctx.get(`${API}/tienda/catalogo/?con_stock=true`)).json();
    await ctx.post(`${API}/tienda/carrito/items/`, {
      data: { producto: catalogo.resultados[0].id, cantidad: 1 },
    });
  }
});

test('comprador completa el checkout, crea el envio y ve su seguimiento', async ({ page }) => {
  await cargarSesion(page);

  await page.goto('/carrito');
  await expect(page.getByText('Proceder al checkout')).toBeVisible();
  await page.getByText('Proceder al checkout').click();

  await page.getByRole('button', { name: /Pagar/ }).click();
  await expect(page.locator('.exito-box')).toBeVisible({ timeout: 20_000 });

  await page.goto('/pedidos');
  await expect(page.getByText('Pendiente de preparacion').first()).toBeVisible({
    timeout: 10_000,
  });
});

test('el personal ve el panel de envios con el envio recien creado', async ({ page }) => {
  await cargarSesion(page);

  await page.goto('/envios');
  await expect(page.locator('h1')).toHaveText('Envios');
  await expect(page.locator('.envio-card').first()).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('.envio-card .badge').first()).toContainText(
    'Pendiente de preparacion',
  );
});
