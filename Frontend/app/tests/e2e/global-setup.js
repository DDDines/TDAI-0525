import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../../../');
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT || '8012';
const frontendPort = process.env.PLAYWRIGHT_FRONTEND_PORT || '4175';
const pythonExe = process.env.PLAYWRIGHT_PYTHON || 'python';

export default async function globalSetup() {
  if (process.env.PLAYWRIGHT_SKIP_DEV_START === '1') {
    return;
  }

  const prepareScriptPath = path.join(repoRoot, 'scripts', 'prepare_e2e_backend.py');
  const scriptPath = path.join(repoRoot, 'scripts', 'dev-start.ps1');

  execFileSync(pythonExe, [prepareScriptPath], {
    cwd: repoRoot,
    stdio: 'inherit',
    env: {
      ...process.env,
      AUTO_CREATE_TABLES: process.env.AUTO_CREATE_TABLES || 'True',
    },
  });

  execFileSync(
    'powershell',
    [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      scriptPath,
      '-BackendPort',
      backendPort,
      '-FrontendPort',
      frontendPort,
      '-WaitForHealth',
    ],
    {
      cwd: repoRoot,
      stdio: 'inherit',
      env: {
        ...process.env,
        VITE_API_BASE_URL: `http://127.0.0.1:${backendPort}/api/v1`,
      },
    }
  );
}
