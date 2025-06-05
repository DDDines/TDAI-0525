🚀 TDAI - Transformador de Dados Assistido por IA 🚀
O TDAI (Transformador de Dados Assistido por IA) é uma solução SaaS inovadora, meticulosamente projetada para automatizar e elevar a qualidade da gestão de catálogos de produtos para e-commerce. A plataforma ingere dados brutos de produtos (de fontes diversas como .xlsx, .csv, .pdf), executa um sofisticado pipeline de enriquecimento web para coletar informações abrangentes, e, finalmente, emprega o poder de Grandes Modelos de Linguagem (LLMs) como GPT e Gemini para gerar títulos e descrições de produtos otimizados para conversão, prontos para serem implantados em qualquer vitrine digital.

Este documento serve como um guia técnico aprofundado para desenvolvedores, detalhando a arquitetura, funcionalidades, fluxos de trabalho, configuração e visão de futuro do TDAI.

📜 Índice Completo
🌟 Visão Geral e Proposta de Valor

🧩 Funcionalidades Centrais Detalhadas

🔩 Backend (FastAPI)

🔑 Módulo de Autenticação e Autorização

📊 Gestão de Planos, Limites e Roles

📂 Pipeline de Ingestão e Processamento de Arquivos

🕸️ Pipeline de Enriquecimento Web Inteligente

🤖 Motor de Geração de Conteúdo com IA

🛍️ Gestão de Produtos e Tipos de Produto

🚚 Gestão de Fornecedores

📋 Histórico de Uso e Logs

📈 Painel de Administração e Analytics

🖥️ Frontend (React)

🖼️ Arquitetura da Interface e Componentização

🔄 Gerenciamento de Estado Global e Local

🔗 Fluxo de Interação com a API

📄 Principais Páginas e Funcionalidades

🏛️ Arquitetura da Solução e Tech Stack

🗺️ Visão Geral da Arquitetura

🛠️ Detalhamento do Tech Stack

⚙️ Guia de Configuração e Deployment Local

✅ Pré-requisitos Essenciais

🔑 Configuração Detalhada das Variáveis de Ambiente (.env)

🔩 Passos Detalhados para Instalação do Backend

🖥️ Passos Detalhados para Instalação do Frontend

🚀 Inicialização e Verificação

📚 Documentação e Endpoints da API (Swagger/ReDoc)

📁 Estrutura Detalhada do Projeto

🌊 Fluxos de Trabalho Principais

👤 Fluxo de Registro e Login de Usuário

🔄 Fluxo Completo de Enriquecimento de Produto (de Upload à Geração IA)

🛡️ Considerações de Segurança

💡 Roadmap Estratégico e Visão de Futuro

🤝 Como Contribuir

📝 Licença

1. 🌟 Visão Geral e Proposta de Valor
O TDAI visa resolver um dos maiores desafios do e-commerce: a criação de conteúdo de produto que seja ao mesmo tempo informativo, atraente e otimizado para mecanismos de busca, em escala. Tradicionalmente, este é um processo manual, demorado e caro.

🎯 Proposta de Valor:

⚡ Automação Inteligente: Reduz drasticamente o tempo e o esforço manual na criação de descrições de produtos.

🏆 Qualidade e Consistência: Garante um alto padrão de qualidade e uniformidade em todo o catálogo.

✨ Otimização para Conversão: Utiliza IA para gerar textos persuasivos e orientados para SEO. (Corrigi o emoji que estava como "конверсия")

📈 Escalabilidade: Permite que empresas de qualquer tamanho enriqueçam milhares de produtos eficientemente.

📊 Tomada de Decisão Baseada em Dados: (Futuro) Oferece insights sobre a qualidade do conteúdo e o potencial de melhoria.

O objetivo final é transformar o TDAI em um "motor semântico" para catálogos de produtos, um sistema que aprende e melhora continuamente, capacitando os usuários a venderem mais e melhor.

2. 🧩 Funcionalidades Centrais Detalhadas
2.1. 🔩 Backend (FastAPI)
O backend é construído com FastAPI, escolhido por sua alta performance, facilidade de uso com tipagem Python e geração automática de documentação.

2.1.1. 🔑 Módulo de Autenticação e Autorização
🚪 Registro de Usuário: (routers/auth_utils.py, crud.py) Novos usuários podem se registrar fornecendo e-mail e senha. A senha é hasheada usando passlib antes de ser armazenada.

🎟️ Login com JWT: (auth.py, core/security.py) Usuários autenticados recebem um JSON Web Token (JWT) que deve ser incluído no header Authorization (Bearer token) para acessar rotas protegidas. O token contém o user_id e um tempo de expiração.

🌐 Login Social (OAuth 2.0): (routers/social_auth.py, core/config.py)

Integração com Google e Facebook utilizando Authlib.

Fluxo detalhado na seção 7.1. Fluxo de Registro e Login de Usuário.

🔑 Recuperação de Senha: (routers/password_recovery.py, core/email_utils.py)

Usuários esquecidos podem solicitar a redefinição de senha. Um token de reset único e com tempo de expiração é gerado e enviado para o e-mail do usuário.

O e-mail utiliza um template HTML (templates/password_reset_email.html).

🕵️ Verificação de Usuário Atual: (auth.py:get_current_active_user) Função de dependência do FastAPI para injetar o usuário autenticado nas rotas protegidas.

2.1.2. 📊 Gestão de Planos, Limites e Roles
👥 Modelos de Dados: User (models.py) possui campos como plan (ex: "free", "pro") e role (ex: "user", "admin").

⚖️ Serviço de Limites: (services/limit_service.py)

Verifica se o usuário possui créditos suficientes antes de realizar operações que consomem IA.

Decrementa os créditos após o uso.

🛡️ Autorização Baseada em Roles: Endpoints específicos (ex: routers/admin_analytics.py) são protegidos para acesso apenas por usuários com role="admin".

2.1.3. 📂 Pipeline de Ingestão e Processamento de Arquivos
📤 Endpoint de Upload: (routers/uploads.py:upload_file)

Aceita UploadFile do FastAPI (.xlsx, .csv, .pdf).

Valida o tipo de arquivo e o tamanho.

⏳ Processamento Assíncrono: Utiliza BackgroundTasks para processar o arquivo sem bloquear a requisição HTTP.

⚙️ Serviço de Processamento: (services/file_processing_service.py)

Leitura: pandas para .xlsx/.csv, pdfplumber para .pdf.

Criação/Atualização: Adiciona/atualiza produtos no banco via crud.

2.1.4. 🕸️ Pipeline de Enriquecimento Web Inteligente
🎯 Endpoint de Enriquecimento: (routers/web_enrichment.py:enrich_product_from_web)

🤖 Serviço de Extração de Dados Web: (services/web_data_extractor_service.py)

Query de Busca: Otimizada para Google.

Google Search API: Obtém URLs relevantes.

Scraping com Playwright: Renderiza páginas dinâmicas.

Extração de Conteúdo: extruct para metadados (JSON-LD, OpenGraph), trafilatura para texto principal.

Armazenamento: Dados coletados são salvos para uso pela IA.

2.1.5. 🤖 Motor de Geração de Conteúdo com IA
💡 Endpoint de Geração: (routers/generation.py:generate_product_content)

🧠 Serviço de Geração IA: (services/ia_generation_service.py)

Seleção do Provedor: Chave pessoal ou global (OpenAI/Gemini).

Construção do Prompt: Detalhado, com dados do produto e instruções claras (exemplo de prompt na seção 2.1.5 da documentação completa).

Chamada à API LLM.

Processamento e Armazenamento: Salva títulos e descrições gerados.

Controle de Limites: Decrementa créditos de IA.

2.1.6. 🛍️ Gestão de Produtos e Tipos de Produto
🧱 Modelos: Product, ProductType, AttributeDefinition (models.py).

ProductType define templates de atributos (ex: "Cor", "Tamanho" para Camiseta).

🧩 CRUD para Produtos: (routers/produtos.py, crud.py) Completo.

🏷️ CRUD para Tipos de Produto: (routers/product_types.py, crud.py).

2.1.7. 🚚 Gestão de Fornecedores
👤 Modelo: Fornecedor (models.py).

🛠️ CRUD para Fornecedores: (routers/fornecedores.py, crud.py).

2.1.8. 📋 Histórico de Uso e Logs
📓 Modelos: LogEntry (no Product), UsoIA (models.py).

📜 Endpoints de Histórico: (routers/uso_ia.py) Para visualização do uso da IA.

2.1.9. 📈 Painel de Administração e Analytics
🔒 Endpoints Protegidos: (routers/admin_analytics.py) Para role="admin".

📊 Dados Agregados: Número de usuários, produtos, gerações de IA, etc.

2.2. 🖥️ Frontend (React)
A interface do usuário é construída com React e Vite, focando em uma experiência moderna, responsiva e eficiente.

2.2.1. 🖼️ Arquitetura da Interface e Componentização
뼈대 App Principal: App.jsx (roteamento com react-router-dom, provedores de contexto).

🏠 Layout Principal: MainLayout.jsx (Sidebar, Topbar, área de conteúdo).

🧩 Componentes Reutilizáveis: (src/components/)

common/Modal.jsx, common/PaginationControls.jsx.

Tabelas (ProductTable.jsx) e Modais (NewProductModal.jsx) específicos.

🎨 Estilização: CSS modular e estilos globais (index.css, App.css).

2.2.2. 🔄 Gerenciamento de Estado Global e Local
🌐 Context API:

AuthContext.jsx: Estado de autenticação global, token JWT no localStorage.

ProductTypeContext.jsx: Tipos de produto.

🏡 Estado Local: useState, useEffect para estado interno dos componentes.

2.2.3. 🔗 Fluxo de Interação com a API
📞 Axios Client: (services/apiClient.js)

Instância pré-configurada com baseURL e Interceptor de Requisição para adicionar token JWT.

📦 Serviços da API: (src/services/)

Módulos encapsulando chamadas aos endpoints (ex: authService.js, productService.js).

2.2.4. 📄 Principais Páginas e Funcionalidades
🔑 LoginPage.jsx: Login, registro, login social.

📊 DashboardPage.jsx: Página inicial pós-login.

🛍️ ProdutosPage.jsx: Listagem, adição, edição de produtos; disparo de enriquecimento/geração IA.

🏷️ TiposProdutoPage.jsx: Gerenciamento de tipos de produto.

🚚 FornecedoresPage.jsx: Gerenciamento de fornecedores.

✨ EnriquecimentoPage.jsx: Interface para processo de enriquecimento.

📜 HistoricoPage.jsx: Histórico de uso da IA.

💳 PlanoPage.jsx: Informações do plano do usuário.

⚙️ ConfiguracoesPage.jsx: Alterar senha, chaves de API pessoais.

🛡️ ProtectedRoute.jsx: Protege rotas autenticadas.

3. 🏛️ Arquitetura da Solução e Tech Stack
3.1. 🗺️ Visão Geral da Arquitetura
O TDAI opera em uma arquitetura cliente-servidor desacoplada:

Backend (Servidor): API RESTful com FastAPI.

Frontend (Cliente): SPA com React.

Banco de Dados: PostgreSQL (SQLAlchemy ORM, Alembic).

Serviços Externos: APIs OpenAI/Gemini, Google Custom Search.

3.2. 🛠️ Detalhamento do Tech Stack
Categoria

Tecnologia/Biblioteca

Propósito

Backend Framework

FastAPI

Criação de APIs Python de alta performance.

Servidor ASGI

Uvicorn

Servidor ASGI para FastAPI.

Linguagem (Backend)

Python 3.8+

Linguagem principal do backend.

Banco de Dados

PostgreSQL

Banco de dados relacional.

ORM & Migrações

SQLAlchemy, Alembic

Mapeamento objeto-relacional e migrações de schema.

Validação de Dados

Pydantic

Definição e validação de schemas de dados da API.

Autenticação

JWT (python-jose), Passlib, Authlib

Tokens, hashing de senhas, OAuth 2.0.

Processamento Arquivos

Pandas, python-multipart, pdfplumber

Leitura de Excel, CSV, PDF.

Web Scraping

Playwright, Extruct, Trafilatura

Automação de navegador, extração de metadados e conteúdo.

Comunicação Externa

google-api-python-client, openai

Clientes para APIs Google e OpenAI.

Tarefas Background

FastAPI BackgroundTasks

Execução assíncrona de tarefas.

Frontend Framework

React 18

Biblioteca JavaScript para UIs componentizadas.

Build Tool (Frontend)

Vite

Ferramenta de build moderna para frontend.

Linguagem (Frontend)

JavaScript (ES6+), JSX

Linguagem principal do frontend.

Roteamento (Frontend)

react-router-dom

Gerenciamento de navegação na SPA.

Estado (FE)

React Context API, useState, useEffect

Gerenciamento de estado global e local.

Chamadas HTTP (FE)

Axios

Cliente HTTP para requisições à API.

UI & Notificações (FE)

CSS modular, react-icons, react-toastify

Estilização, ícones e feedback ao usuário.

4. ⚙️ Guia de Configuração e Deployment Local
4.1. ✅ Pré-requisitos Essenciais
🐍 Python 3.8+

📦 Node.js 18.0.0+ (com npm)

🐘 PostgreSQL 12+ (servidor ativo, banco e usuário criados)

🐙 Git

🌐 Playwright Browsers (playwright install)

🔑 Chaves de API (OpenAI, Google Search, OAuth opcional)

4.2. 🔑 Configuração Detalhada das Variáveis de Ambiente (.env)
Crie um arquivo .env na raiz do projeto. Não o versione no Git!

# .env (Exemplo - Preencha com seus valores)

# --- 🐘 Banco de Dados ---
DATABASE_URL="postgresql://seu_usuario_pg:sua_senha_pg@localhost:5432/seu_banco_tdai"

# --- 🤫 Segurança da Aplicação ---
SECRET_KEY="SUA_CHAVE_SECRETA_FORTE_AQUI_GERADA_COM_OPENSSL_RAND_HEX_32"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# --- 📧 Configurações de E-mail ---
SMTP_SERVER="smtp.example.com"
SMTP_PORT=587
SMTP_USER="seu-email-de-envio@example.com"
SMTP_PASSWORD="sua-senha-de-aplicativo-ou-smtp"
EMAIL_FROM="TDAI Platform <nao-responda@tdai.com>"

# --- 🌐 URL do Frontend ---
FRONTEND_URL="http://localhost:5173"

# --- 🤖 Chaves de API (IA e Busca) ---
OPENAI_API_KEY="sk-SUA_CHAVE_OPENAI_AQUI"
GOOGLE_CSE_ID="SEU_CUSTOM_SEARCH_ENGINE_ID"
GOOGLE_CSE_API_KEY="SUA_GOOGLE_API_KEY"

# --- 🔗 Chaves de OAuth 2.0 (Opcional) ---
# GOOGLE_CLIENT_ID="SEU_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
# GOOGLE_CLIENT_SECRET="SEU_GOOGLE_CLIENT_SECRET"
# FACEBOOK_CLIENT_ID="SEU_FACEBOOK_APP_ID"
# FACEBOOK_CLIENT_SECRET="SEU_FACEBOOK_APP_SECRET"

Nota: O código em database.py tem fallback para SQLite se DATABASE_URL não for PostgreSQL, útil para testes rápidos.

4.3. 🔩 Passos Detalhados para Instalação do Backend
Clone o Repositório:

git clone <URL_DO_SEU_REPOSITORIO_GIT>
cd <NOME_DA_PASTA_DO_PROJETO>

Crie e Ative Ambiente Virtual Python:

python -m venv venv
source venv/bin/activate  # Linux/macOS
# .\venv\Scripts\activate # Windows

Instale Dependências Python:
(Certifique-se de ter um Backend/requirements.txt com todas as dependências listadas)

pip install -r Backend/requirements.txt

Instale Navegadores Playwright:

playwright install

Configure Banco PostgreSQL:

Crie usuário e banco (ex: CREATE USER seu_usuario_pg WITH PASSWORD 'sua_senha_pg'; CREATE DATABASE seu_banco_tdai OWNER seu_usuario_pg;).

Verifique DATABASE_URL no .env.

Execute Migrações Alembic:

cd Backend
alembic upgrade head
cd ..

4.4. 🖥️ Passos Detalhados para Instalação do Frontend
Navegue até a Pasta do Frontend:

cd Frontend/app

Instale Dependências Node.js:

npm install
# ou: yarn install

4.5. 🚀 Inicialização e Verificação
Inicie o Backend: (Na raiz do projeto)

python run_backend.py

(Disponível em http://localhost:8000)

Inicie o Frontend: (Em Frontend/app, novo terminal)

npm run dev
# ou: yarn dev

(Disponível em http://localhost:5173)

Verifique:

Abra http://localhost:5173 no navegador.

Acesse API docs: http://localhost:8000/docs ou http://localhost:8000/redoc.

5. 📚 Documentação e Endpoints da API (Swagger/ReDoc)
Acesse a documentação interativa da API gerada pelo FastAPI:

Swagger UI: http://localhost:8000/docs (Ideal para testar endpoints)

ReDoc: http://localhost:8000/redoc (Visualização mais limpa)

6. 📁 Estrutura Detalhada do Projeto
TDAI_Project_Root/
├── 🔩 Backend/
│   ├── alembic/            # Migrações Alembic
│   ├── core/               # Configurações centrais, email, segurança
│   ├── routers/            # Endpoints da API (FastAPI)
│   ├── services/           # Lógica de negócios (IA, scraping, arquivos)
│   ├── templates/          # Templates HTML (e-mails)
│   ├── auth.py             # Utilitários de autenticação FastAPI
│   ├── crud.py             # Funções CRUD diretas ao banco
│   ├── database.py         # Configuração da conexão SQLAlchemy
│   ├── main.py             # Ponto de entrada FastAPI
│   ├── models.py           # Modelos de dados SQLAlchemy
│   └── schemas.py          # Schemas Pydantic (validação API)
│
├── 🖥️ Frontend/
│   └── app/                # Raiz da aplicação React (Vite)
│       ├── public/         # Arquivos estáticos
│       ├── src/
│       │   ├── components/ # Componentes React reutilizáveis
│       │   ├── contexts/   # React Context API (estado global)
│       │   ├── pages/      # Componentes de página
│       │   ├── services/   # Lógica de chamada à API
│       │   ├── utils/      # Utilitários
│       │   ├── App.jsx     # Componente raiz e roteamento
│       │   └── main.jsx    # Ponto de entrada React
│       ├── vite.config.js  # Configuração do Vite (proxy, etc.)
│       └── package.json    # Dependências e scripts Node.js
│
├── 📜 Prototipos/           # Documentos de visão e design
│
├── .env                    # ⚠️ ARQUIVO LOCAL: Variáveis de ambiente (NÃO VERSIONAR)
├── README.md               # ✨ Este arquivo de documentação
├── requirements.txt        # (SUGERIDO) Dependências Python do Backend
└── run_backend.py          # Script para iniciar backend

7. 🌊 Fluxos de Trabalho Principais
7.1. 👤 Fluxo de Registro e Login de Usuário
Registro (Frontend): Formulário (LoginPage.jsx) -> authService.register() -> POST /api/v1/auth/register (Backend).

Login Local (Frontend): Formulário (LoginPage.jsx) -> AuthContext.login() -> authService.login() -> POST /api/v1/auth/token (Backend) -> JWT retornado e armazenado.

Login Social (OAuth - Ex: Google): Botão -> GET /api/v1/auth/google/login (Backend) -> Redirecionamento Google -> Callback GET /api/v1/auth/google/callback (Backend) -> Troca código por token Google -> Obtém perfil -> Cria/Loga usuário TDAI -> Gera JWT TDAI.

7.2. 🔄 Fluxo Completo de Enriquecimento de Produto (de Upload à Geração IA)
Upload (Frontend): Seleciona arquivo -> productService.uploadFile() -> POST /api/v1/uploads/.

Processamento Inicial (Backend): routers/uploads.py -> BackgroundTasks com file_processing_service -> Leitura (Pandas/pdfplumber) -> Cria/Atualiza produtos via crud.

Disparo Enriquecimento Web (Frontend): Seleciona produtos -> "Enriquecer" -> productService.enrichProduct() -> POST /api/v1/web-enrichment/{product_id}/enrich.

Pipeline Enriquecimento Web (Backend): web_data_extractor_service -> Google Search -> Playwright/Extruct/Trafilatura -> Salva dados extraídos.

Disparo Geração IA (Frontend): Seleciona produto -> "Gerar Conteúdo" -> productService.generateContent() -> POST /api/v1/generation/{product_id}/generate.

Pipeline Geração IA (Backend): limit_service (créditos) -> ia_generation_service -> Constrói Prompt -> Chama LLM -> Salva conteúdo gerado.

Visualização (Frontend): ProdutosPage.jsx exibe conteúdos -> Usuário seleciona.

8. 🛡️ Considerações de Segurança
🔒 Senhas: Hasheadas com bcrypt (passlib).

🔑 JWT: Autenticação stateless. SECRET_KEY forte e HTTPS em produção são cruciais.

🔗 OAuth 2.0: Authlib seguindo fluxos padrão. client_secrets protegidos.

🌐 CORS: Configurado no Backend (main.py) para FRONTEND_URL.

✅ Validação de Entrada: Pydantic (schemas.py) no backend.

🛡️ XSS/CSRF: React escapa dados (XSS). JWT em header Authorization reduz risco CSRF.

📦 Dependências: Manter atualizadas (Python & Node.js).

🕷️ Playwright: Respeitar robots.txt e evitar sobrecarga em sites alvo.

9. 💡 Roadmap Estratégico e Visão de Futuro
A visão para o TDAI é ambiciosa, conforme detalhado nos documentos Prototipos/TDAI FUTURE.pdf:

Fase 1: Fundação Sólida (Atual)

Enriquecimento e geração IA de alta qualidade.

Interface intuitiva.

Fase 2: Inteligência Aprimorada e Automação Avançada

🤖 Agentes de IA Autônomos (CrewAI/LangGraph): Sistema multi-agente para enriquecimento.

💯 Score de Qualidade de Conteúdo: Avaliação automática da "saúde" do conteúdo.

🗣️ Aprendizado Contínuo com Feedback: Refinamento de prompts e modelos.

📝 Templates de Prompt Dinâmicos: Customização por usuários avançados.

Fase 3: Ecossistema de Conteúdo e Integrações

📢 Otimização Multi-Canal: Variações para diferentes marketplaces.

🖼️ Enriquecimento de Mídia Avançado: Análise de imagens, remoção de fundo, alt-text.

🔌 Publicação Direta e Sincronização: Integração com plataformas e-commerce/ERPs.

Fase 4: Personalização e Inteligência Preditiva

🎯 Personalização em Massa: Descrições adaptadas a personas.

🔮 Análise Preditiva de Tendências: Sugestões de otimizações de catálogo.

10. 🤝 Como Contribuir
Contribuições são super bem-vindas! ✨

🗣️ Discuta Primeiro: Abra uma Issue para discutir sua ideia ou bug.

🍴 Fork & Branch: Faça um Fork e crie uma branch (feature/sua-feature ou fix/seu-bug).

💻 Desenvolva: Siga as convenções (PEP 8, ESLint). Código claro e comentado.

🧪 Teste: Adicione/atualize testes. Garanta que todos passem.

📖 Documente: Atualize o README.md ou outra documentação se necessário.

💾 Commit & Push: Commits atômicos (feat: ..., fix: ...). Push para seu fork.

🚀 Pull Request (PR): Abra um PR para a branch main (ou develop) do oficial. Descreva suas alterações.

11. 📝 Licença
(Defina a licença do seu projeto aqui. Ex: MIT, Apache 2.0, GPL, etc.)

Exemplo:
Este projeto é licenciado sob a Licença MIT - veja o arquivo LICENSE.md para detalhes.

Este README.md agora é um documento muito mais completo, pronto para guiar qualquer pessoa através do seu impressionante projeto TDAI!