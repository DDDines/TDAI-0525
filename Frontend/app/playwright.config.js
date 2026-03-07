import { defineConfig } from '@playwright/test';

const frontendPort = process.env.PLAYWRIGHT_FRONTEND_PORT || '4175';
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT || '8012';

process.env.PLAYWRIGHT_FRONTEND_PORT = frontendPort;
process.env.PLAYWRIGHT_BACKEND_PORT = backendPort;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: {
    timeout: 15_000,
  },
  reporter: 'list',
  globalSetup: './tests/e2e/global-setup.js',
  globalTeardown: './tests/e2e/global-teardown.js',
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
      },
    },
  ],
});
