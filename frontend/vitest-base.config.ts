// Learn more about Vitest configuration options at https://vitest.dev/config/
//
// Configuracion base de Vitest para el runner de Angular
// (@angular/build:unit-test). Se carga a traves de la opcion
// "runnerConfig": true del target "test" de angular.json.
// Nota: el runner sobreescribe test.projects y test.include.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // La suite declara describe/it/expect/vi de forma global
    // (ver "types": ["vitest/globals"] en tsconfig.spec.json).
    globals: true,
    environment: 'jsdom',
    restoreMocks: true,
  },
});
