import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../../../');
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT || '8012';
const frontendPort = process.env.PLAYWRIGHT_FRONTEND_PORT || '4175';

export default async function globalTeardown() {
  if (process.env.PLAYWRIGHT_SKIP_DEV_START === '1') {
    return;
  }

  const scriptPath = path.join(repoRoot, 'scripts', 'dev-stop.ps1');

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
    ],
    {
      cwd: repoRoot,
      stdio: 'inherit',
    }
  );
}
