# Documentação Completa de Funções — Frontend
---

## Frontend/app/README.md

* **Sem funções**: Documentação do frontend.

## Dependência para pré-visualização de PDF

* A geração de previews de PDF depende do pacote `poppler-utils` instalado no sistema (por exemplo, `apt install poppler-utils`). Sem ele o backend não consegue converter PDFs em imagens, e o frontend não exibirá a pré-visualização do arquivo.

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

* `Modal({ isOpen, onClose, title, children })`: Componente modal genérico. Recebe props para exibir formulários ou mensagens, controla abertura/fechamento, e define ações de confirmação/cancelamento.

## Frontend/app/src/common/PaginationControls.jsx

* `PaginationControls({ currentPage, totalPages, onPageChange, isLoading, itemsPerPage, onItemsPerPageChange, totalItems })`: Componente de paginação. Recebe props para controlar página atual, total de itens e ações de navegação (próxima, anterior).

## Frontend/app/src/common/PdfRegionSelector.jsx

* `PdfRegionSelector({ file, onSelect })`: Permite desenhar uma região em um PDF e envia as coordenadas ao callback.

---

## Frontend/app/src/components/product_types/AttributeTemplateList.jsx

* `AttributeTemplateList({ attributes, onEdit, onDelete, onReorder })`: Lista templates de atributos de produto, exibe botões de editar/deletar e dispara callbacks recebidos via props.

## Frontend/app/src/components/product_types/AttributeTemplateModal.jsx

* `AttributeTemplateModal({ isOpen, onClose, attribute, onSave, isSubmitting })`: Modal para criação/edição de template de atributos. Recebe props para controlar abertura, template ativo e callback de salvar.

## Frontend/app/src/components/fornecedores/EditFornecedorModal.jsx

* `EditFornecedorModal({ isOpen, onClose, fornecedorData, onSave, isLoading })`: Modal para editar dados de um fornecedor. Conta agora com a aba **Arquivos**, que lista catálogos enviados e permite reprocessá-los. Na aba **Importar Catálogo**, o botão abre o `ImportCatalogWizard`.

## Frontend/app/src/components/fornecedores/ImportCatalogWizard.jsx

* `ImportCatalogWizard({ isOpen, onClose, fornecedorId })`: Assistente em três passos para importar catálogos.
  1. **Pré-visualização e seleção do tipo** – upload do arquivo, exibição de amostras e escolha do tipo de produto.
  2. **Mapeamento de colunas** – associa colunas da planilha a campos padrão e atributos dinâmicos. Permite criar um novo tipo de produto caso não exista.
  3. **Confirmação** – revisão final e importação.
O wizard mostra linhas de amostra e miniaturas antes do envio definitivo, garantindo que as colunas estejam corretas.
  Durante a pré-visualização é possível clicar em **Pré-visualizar texto** para extrair o texto completo da página atual do PDF. O sistema chama `fornecedorService.selecionarRegiao` cobrindo toda a página e exibe o resultado em um modal para verificação.

## Frontend/app/src/components/fornecedores/CatalogFileList.jsx

* `CatalogFileList({ files = [], onReprocess })`: Exibe tabela com arquivos importados, mostrando link de download e botão opcional de reprocessar.

## Frontend/app/src/components/fornecedores/FornecedorTable.jsx

* `FornecedorTable({ fornecedores, onRowClick, onSelectRow, selectedIds, onSelectAllRows, isLoading })`: Tabela que exibe fornecedores cadastrados. Permite editar/deletar via callbacks recebidos.

## Frontend/app/src/components/MainLayout.jsx

* `MainLayout()`: Componente de layout principal. Renderiza menu lateral (Sidebar), barra superior (Topbar) e área principal (`children`).

## Frontend/app/src/components/fornecedores/NewFornecedorModal.jsx

* `NewFornecedorModal({ isOpen, onClose, onSave, isLoading })`: Modal para cadastro de novo fornecedor. Recebe props para abertura/fechamento e callback de salvar.

## Frontend/app/src/components/produtos/NewProductModal.jsx

* `NewProductModal({ isOpen, onClose, onSave, isLoading, productTypes, loadingProductTypes })`: Modal para cadastro de novo produto. Props para controle de abertura/fechamento e callback de salvar.

## Frontend/app/src/components/ProductEditModal.jsx

* `ProductEditModal({ isOpen, onClose, product, onProductUpdated })`: Modal para editar produto já existente. Props para abertura, produto ativo e salvar.

## Frontend/app/src/components/produtos/ProductTable.jsx

* `ProductTable({ produtos, onEdit, onSort, sortConfig, onSelectProduto, selectedProdutos, onSelectAllProdutos, loading })`: Tabela que lista todos os produtos cadastrados. Permite editar/deletar via callbacks.

## Frontend/app/src/components/ProtectedRoute.jsx

* `ProtectedRoute({ children, allowedRoles })`: Wrapper para proteger rotas; exige autenticação. Redireciona para login se usuário não estiver autenticado.

## Frontend/app/src/components/Sidebar.jsx

* `Sidebar({ isOpen, toggleSidebar })`: Menu lateral de navegação. Recebe lista de links/menu via props.

## Frontend/app/src/components/Topbar.jsx

* `Topbar({ viewTitle })`: Barra superior. Exibe usuário logado, botão de logout e atalhos do sistema.

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

* `AttributeField({ attributeTemplate, value, onChange, disabled })`: Componente para campo de atributo dinâmico em formulários de produto. Renderiza campo de input/select conforme tipo do atributo. Dispara callback ao alterar valor.

### Instruções de gerenciamento de arquivos

Na aba **Arquivos** do `EditFornecedorModal` é possível visualizar catálogos já enviados. Clique no nome para baixar o arquivo ou use **Reprocessar** para importá-lo novamente. Durante o assistente de importação, o `PdfRegionSelector` ajuda a escolher a região do PDF contendo a tabela de produtos.

---

## Frontend/app/vite.config.js

* **Configuração**: Arquivo de configuração do Vite (bundler do projeto). Define plugins, paths e otimizações de build.

---

