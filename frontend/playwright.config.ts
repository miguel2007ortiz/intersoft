import { defineConfig, devices } from '@playwright/test';

const PUERTO_FRONTEND = Number(process.env.FRONTEND_PORT ?? 4200);

/**
 * E2E del frontend: cubre el happy path del marketplace (login, carrito,
 * checkout que crea el envio, seguimiento en "Mis pedidos" y el panel de
 * Envios del personal). Reduce el riesgo pendiente n.º 4 de docs/RIESGOS.md.
 *
 * Requisitos para correr local:
 *  1. Backend en desarrollo apuntando a la BD `intersoft1_db` migrada y con
 *     datos de demostracion (python manage.py migrate; seed_demo) elevado en
 *     127.0.0.1:8000 (el frontend de desarrollo usa environment.ts).
 *  2. `npm run test:e2e` levanta `ng serve` solo; el backend se inicia aparte.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${PUERTO_FRONTEND}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npx ng serve --port ${PUERTO_FRONTEND} --host 127.0.0.1`,
    url: `http://127.0.0.1:${PUERTO_FRONTEND}`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
