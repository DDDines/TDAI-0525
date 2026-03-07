module.exports = {
  testEnvironment: 'jsdom',
  setupFiles: ['<rootDir>/jest.setup.js'],
  testPathIgnorePatterns: ['<rootDir>/tests/e2e/'],
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/**/__tests__/**',
    '!src/**/*.test.{js,jsx}',
    '!src/main.jsx',
  ],
  coverageThreshold: {
    global: {
      statements: 50,
      branches: 45,
      functions: 50,
      lines: 52,
    },
    './src/App.jsx': {
      statements: 100,
      branches: 75,
      functions: 100,
      lines: 100,
    },
    './src/components/MainLayout.jsx': {
      statements: 100,
      branches: 50,
      functions: 100,
      lines: 100,
    },
    './src/components/Sidebar.jsx': {
      statements: 100,
      branches: 80,
      functions: 100,
      lines: 100,
    },
    './src/services/apiClient.js': {
      statements: 100,
      branches: 80,
      functions: 100,
      lines: 100,
    },
    './src/services/configService.js': {
      statements: 100,
      branches: 75,
      functions: 100,
      lines: 100,
    },
    './src/services/productService.js': {
      statements: 75,
      branches: 35,
      functions: 100,
      lines: 75,
    },
    './src/services/fornecedorService.js': {
      statements: 50,
      branches: 10,
      functions: 100,
      lines: 50,
    },
    './src/services/adminService.js': {
      statements: 85,
      branches: 60,
      functions: 100,
      lines: 85,
    },
    './src/services/historicoService.js': {
      statements: 100,
      branches: 0,
      functions: 100,
      lines: 100,
    },
    './src/services/productTypeService.js': {
      statements: 100,
      branches: 0,
      functions: 100,
      lines: 100,
    },
    './src/services/searchService.js': {
      statements: 100,
      branches: 75,
      functions: 100,
      lines: 100,
    },
    './src/services/usoIAService.js': {
      statements: 75,
      branches: 35,
      functions: 100,
      lines: 75,
    },
    './src/contexts/AuthContext.jsx': {
      statements: 85,
      branches: 60,
      functions: 100,
      lines: 85,
    },
    './src/contexts/AppExperienceContext.jsx': {
      statements: 90,
      branches: 65,
      functions: 85,
      lines: 90,
    },
    './src/contexts/ProductTypeContext.jsx': {
      statements: 70,
      branches: 50,
      functions: 85,
      lines: 70,
    },
    './src/pages/FornecedoresPage.jsx': {
      statements: 60,
      branches: 30,
      functions: 50,
      lines: 60,
    },
    './src/pages/ConfiguracoesPage.jsx': {
      statements: 85,
      branches: 55,
      functions: 85,
      lines: 85,
    },
    './src/pages/HistoricoPage.jsx': {
      statements: 85,
      branches: 75,
      functions: 90,
      lines: 85,
    },
    './src/pages/PlanoPage.jsx': {
      statements: 100,
      branches: 90,
      functions: 100,
      lines: 100,
    },
    './src/pages/ProdutoConteudoPage.jsx': {
      statements: 80,
      branches: 70,
      functions: 85,
      lines: 85,
    },
    './src/pages/ProdutosPage.jsx': {
      statements: 70,
      branches: 60,
      functions: 65,
      lines: 70,
    },
    './src/pages/RecuperarSenhaPage.jsx': {
      statements: 100,
      branches: 80,
      functions: 100,
      lines: 100,
    },
    './src/pages/ResetSenhaPage.jsx': {
      statements: 90,
      branches: 60,
      functions: 100,
      lines: 90,
    },
    './src/pages/TiposProdutoPage.jsx': {
      statements: 85,
      branches: 60,
      functions: 100,
      lines: 90,
    },
    './src/utils/backend.js': {
      statements: 100,
      branches: 80,
      functions: 100,
      lines: 100,
    },
  },
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest'
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(png|jpg|jpeg|gif|svg)$': '<rootDir>/__mocks__/fileMock.js'
  }
};
