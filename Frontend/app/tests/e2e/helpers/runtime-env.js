import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../../../../');
const envFilePath = path.join(repoRoot, '.env');

function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  return fs
    .readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .reduce((acc, line) => {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) {
        return acc;
      }
      const separatorIndex = trimmed.indexOf('=');
      if (separatorIndex <= 0) {
        return acc;
      }
      const key = trimmed.slice(0, separatorIndex).trim();
      let value = trimmed.slice(separatorIndex + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      acc[key] = value;
      return acc;
    }, {});
}

const repoEnv = parseEnvFile(envFilePath);

export const e2eEmail =
  process.env.E2E_ADMIN_EMAIL ||
  process.env.FIRST_SUPERUSER_EMAIL ||
  process.env.ADMIN_EMAIL ||
  repoEnv.FIRST_SUPERUSER_EMAIL ||
  repoEnv.ADMIN_EMAIL ||
  'admin@example.com';

export const e2ePassword =
  process.env.E2E_ADMIN_PASSWORD ||
  process.env.FIRST_SUPERUSER_PASSWORD ||
  process.env.ADMIN_PASSWORD ||
  repoEnv.FIRST_SUPERUSER_PASSWORD ||
  repoEnv.ADMIN_PASSWORD ||
  'password';
