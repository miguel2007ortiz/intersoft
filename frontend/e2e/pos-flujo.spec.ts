import { expect, test } from '@playwright/test';

/**
 * Happy path del Punto de Venta con rol personal interno (cierra el pendiente
 * de docs/RIESGOS.md: "un e2e del flujo POS con rol personal").
 *
 * Requiere backend en 127.0.0.1:8000 con BD `intersoft1_db` migrada y
 * seed_demo aplicado. Usa el personal demo del seed (luis@elprogreso.co /
 * demo12345, rol EMPLEADO) que seed_demo garantiza con password usable.
 *
 * El POS auto-selecciona el cliente generico de "venta rapida" al cargar,
 * asi que no hace falta elegirlo en la UI.
 */
const USUARIO = { email: 'luis@elprogreso.co', pass: 'demo12345' };

async function cargarSesion(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/login');
  await page.locator('#email').fill(USUARIO.email);
  await page.locator('#password').fill(USUARIO.pass);
  await page.getByRole('button', { name: 'Iniciar sesion' }).click();
  await page.waitForFunction(() => window.localStorage.getItem('intersoft.token') !== null, null, {
    timeout: 20_000,
  });
}

test('el personal realiza una venta de mostrador en el POS', async ({ page }) => {
  await cargarSesion(page);

  await page.goto('/pos');
  await expect(page.locator('h1')).toHaveText('Punto de Venta');

  // Buscar por SKU del seed y agregar el producto a la venta.
  await page.locator('input[placeholder="Buscar por nombre o SKU..."]').fill('SKU-001');
  await expect(page.locator('.resultado-item').first()).toBeVisible({ timeout: 10_000 });
  await page.locator('.resultado-item').first().click();

  // Aparece la linea con el producto y el boton Confirmar se habilita.
  await expect(page.locator('.tabla-lineas')).toBeVisible();
  await expect(page.locator('.btn-confirmar')).toBeEnabled();

  await page.locator('.btn-confirmar').click();
  await expect(page.locator('.exito-box')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.exito-box')).toContainText('Venta registrada!');
});