import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const eslintPath = path.join(__dirname, 'node_modules', '@eslint', 'js');
if (!fs.existsSync(eslintPath)) {
  console.warn('Aviso: dependências do ESLint não encontradas. Execute "npm install" para instalar os pacotes de desenvolvimento.');
}
