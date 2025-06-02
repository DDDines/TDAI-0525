// Frontend/app/vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc' // Seu plugin React atual

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // Mantém a porta padrão do Vite, ou a que você estiver usando
    proxy: {
      // Redirecionar requisições que começam com /api/v1 para o seu backend FastAPI
      '/api/v1': {
        target: 'http://localhost:8000', // URL do seu backend FastAPI
        changeOrigin: true, // Necessário para virtual hosted sites
        // secure: false, // Descomente se o seu backend estiver rodando em HTTPS com certificado autoassinado
        // O rewrite não deve ser necessário aqui, pois seus endpoints FastAPI
        // já estão esperando o prefixo /api/v1 (conforme incluído em Backend/main.py)
        // Exemplo de rewrite (SE NECESSÁRIO, mas provavelmente não é o seu caso):
        // rewrite: (path) => path.replace(/^\/api\/v1/, '')
      }
    }
  }
})