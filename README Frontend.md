# Documentação Completa de Funções — Frontend
---

## Frontend/app/README.md

* **Sem funções**: Documentação do frontend.

## Frontend/app/eslint.config.js

* **Configuração**: Arquivo de configuração do ESLint para garantir o padrão e a qualidade do código JavaScript/React.

## Frontend/app/index.html

* **Estrutura base**: HTML base do app React, define ponto de montagem da SPA.

## Frontend/app/package-lock.json

* **Sem funções**: Arquivo gerado automaticamente pelo npm para controle de dependências exatas.

## Frontend/app/package.json

* **Sem funções**: Define scripts, dependências e metadados do frontend.

## Frontend/app/public/vite.svg

* **Sem funções**: Asset de imagem usado no projeto.

---

## Frontend/app/src/App.css

* **Sem funções**: Arquivo de estilos CSS global.

## Frontend/app/src/App.jsx

* `App()`: Componente principal. Monta o sistema de rotas, provê contexto global (usuário, temas) e define a estrutura base (layout, navegação e proteção de rotas).

---

## Frontend/app/src/assets/react.svg

* **Sem funções**: Ícone do React, usado em assets.

## Frontend/app/src/assets/vite.svg

* **Sem funções**: Ícone do Vite, usado em assets.

---

## Frontend/app/src/common/Modal.jsx

* `Modal(props)`: Componente modal genérico. Recebe props para exibir formulários ou mensagens, controla abertura/fechamento, e define ações de confirmação/cancelamento.

## Frontend/app/src/common/PaginationControls.jsx

* `PaginationControls(props)`: Componente de paginação. Recebe props para controlar página atual, total de itens e ações de navegação (próxima, anterior).

---

## Frontend/app/src/components/product_types/AttributeTemplateList.jsx

* `AttributeTemplateList({ templates, onEdit, onDelete })`: Lista templates de atributos de produto, exibe botões de editar/deletar e dispara callbacks recebidos via props.

## Frontend/app/src/components/product_types/AttributeTemplateModal.jsx

* `AttributeTemplateModal({ isOpen, onClose, template, onSave })`: Modal para criação/edição de template de atributos. Recebe props para controlar abertura, template ativo e callback de salvar.

## Frontend/app/src/components/fornecedores/EditFornecedorModal.jsx

* `EditFornecedorModal({ isOpen, onClose, fornecedor, onSave })`: Modal para editar dados de um fornecedor. Recebe props para controlar abertura, fornecedor ativo e callback de salvar.

## Frontend/app/src/components/fornecedores/FornecedorTable.jsx

* `FornecedorTable({ fornecedores, onEdit, onDelete })`: Tabela que exibe fornecedores cadastrados. Permite editar/deletar via callbacks recebidos.

## Frontend/app/src/components/MainLayout.jsx

* `MainLayout({ children })`: Componente de layout principal. Renderiza menu lateral (Sidebar), barra superior (Topbar) e área principal (`children`).

## Frontend/app/src/components/fornecedores/NewFornecedorModal.jsx

* `NewFornecedorModal({ isOpen, onClose, onSave })`: Modal para cadastro de novo fornecedor. Recebe props para abertura/fechamento e callback de salvar.

## Frontend/app/src/components/produtos/NewProductModal.jsx

* `NewProductModal({ isOpen, onClose, onSave })`: Modal para cadastro de novo produto. Props para controle de abertura/fechamento e callback de salvar.

## Frontend/app/src/components/ProductEditModal.jsx

* `ProductEditModal({ isOpen, onClose, produto, onSave })`: Modal para editar produto já existente. Props para abertura, produto ativo e salvar.

## Frontend/app/src/components/produtos/ProductTable.jsx

* `ProductTable({ produtos, onEdit, onDelete })`: Tabela que lista todos os produtos cadastrados. Permite editar/deletar via callbacks.

## Frontend/app/src/components/ProtectedRoute.jsx

* `ProtectedRoute({ children })`: Wrapper para proteger rotas; exige autenticação. Redireciona para login se usuário não estiver autenticado.

## Frontend/app/src/components/Sidebar.jsx

* `Sidebar({ links })`: Menu lateral de navegação. Recebe lista de links/menu via props.

## Frontend/app/src/components/Topbar.jsx

* `Topbar({ user, onLogout })`: Barra superior. Exibe usuário logado, botão de logout e atalhos do sistema.

---



## Frontend/app/src/index.css

* **Sem funções**: Arquivo de estilos CSS global principal.

## Frontend/app/src/main.jsx

* `main()`: Função principal que inicializa o app React no elemento root da página HTML.

---

## Frontend/app/src/pages/

* *(Pasta reservada para páginas principais do sistema, como Dashboard, Login, etc. Cada página pode conter funções/comportamentos próprios conforme o arquivo implementado.)*

---

## Frontend/app/src/components/produtos/shared/AttributeField.jsx

* `AttributeField({ atributo, valor, onChange })`: Componente para campo de atributo dinâmico em formulários de produto. Renderiza campo de input/select conforme tipo do atributo. Dispara callback ao alterar valor.

---

## Frontend/app/vite.config.js

* **Configuração**: Arquivo de configuração do Vite (bundler do projeto). Define plugins, paths e otimizações de build.

---

