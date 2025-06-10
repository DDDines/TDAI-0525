# TDAI - Backend do Sistema Inteligente de Geração de Títulos e Descrições

Este é o backend para o projeto TDAI (Titles and Descriptions Artificial Intelligence), um sistema SaaS projetado para auxiliar na gestão e enriquecimento de informações de produtos de e-commerce, com foco em geração de conteúdo por IA.

## 📜 Sobre o Projeto

O TDAI visa processar listas de itens de produtos (inicialmente automotivos, mas com potencial de expansão), que muitas vezes chegam com informações mínimas via planilhas ou catálogos PDF. O sistema enriquece essas informações buscando dados na web (sites de fornecedores, catálogos, Google Search) e, por fim, gera títulos e descrições otimizados utilizando inteligência artificial. O backend é construído com FastAPI e PostgreSQL.

## ✨ Funcionalidades Principais do Backend

* **Autenticação e Autorização:**
    * Registo de utilizadores e login com JWT (JSON Web Tokens).
    * Recuperação de senha por email.
    * Login social com Google e Facebook (OAuth) (endpoint de callback em `routers/social_auth.py` a ser verificado/corrigido).
    * Gestão de Roles (ex: `free_user`, `admin`) e Planos de assinatura (ex: Gratuito, Ilimitado).
    * Proteção de rotas baseada em utilizador autenticado e superusuário (`routers/auth_utils.py`).
* **Gestão de Dados:**
    * CRUD completo para `Produtos` (`routers/produtos.py`).
    * CRUD completo para `Fornecedores` (`routers/fornecedores.py`).
    * Associação de produtos a fornecedores e utilizadores.
* **Processamento e Enriquecimento de Produtos:**
    * Upload de ficheiros (Excel, CSV, PDF) para criação de produtos em lote (`routers/uploads.py`, `services/file_processing_service.py`).
    * Enriquecimento web automatizado via tarefas de fundo (`routers/web_enrichment.py`, `services/web_data_extractor_service.py`):
        * Busca de informações no Google (Google Custom Search API).
        * Scraping de conteúdo de páginas web com Playwright.
        * Extração de texto principal (Trafilatura) e metadados estruturados (Extruct).
        * Extração de dados adicionais com LLM (OpenAI).
    * Armazenamento do status e log do processo de enriquecimento (`models.Produto.status_enriquecimento_web`, `log_enriquecimento_web`).
* **Geração de Conteúdo com IA:**
    * Geração de títulos e descrições de produtos utilizando a API da OpenAI via tarefas de fundo (`routers/generation.py`, `services/ia_generation_service.py`).
    * Gestão de chaves de API OpenAI (global em `core/config.py` e por utilizador em `models.User`).
    * Registo de histórico de uso da IA (`models.UsoIA`, `routers/uso_ia.py`).
    * Sistema de verificação de limites de uso da IA baseado no plano do utilizador (`services/limit_service.py`).
* **Administração:**
    * Endpoints para analytics (contagens globais, uso da IA por plano/tipo, atividade de utilizadores) (`routers/admin_analytics.py`).
    * Criação automática de roles, planos e um utilizador administrador na inicialização do sistema (`main.py` evento de startup).

## 🛠️ Tecnologias Utilizadas

* **Framework:** FastAPI
* **Banco de Dados:** PostgreSQL
* **ORM:** SQLAlchemy
* **Validação de Dados:** Pydantic
* **Autenticação:** JWT, Passlib (para hashing de senhas), Authlib (para OAuth)
* **Processamento Assíncrono:** `async/await`, `BackgroundTasks` do FastAPI
* **Web Scraping/Extração:** Playwright, Trafilatura, Extruct, Google Custom Search API
* **IA:** OpenAI API
* **Envio de Emails:** FastAPI-Mail

## 📂 Estrutura do Projeto Backend

A pasta `Backend/` contém toda a lógica da API e está organizada da seguinte forma:

Backend/
├── core/                 # Configurações centrais, lógica de email, etc.
│   ├── init.py
│   ├── config.py         # Carrega variáveis de ambiente, define settings.
│   └── email_utils.py    # Utilitários para envio de email.
├── routers/              # Define os endpoints da API.
│   ├── init.py
│   ├── admin_analytics.py
│   ├── auth_utils.py
│   ├── fornecedores.py
│   ├── generation.py
│   ├── password_recovery.py
│   ├── produtos.py
│   ├── social_auth.py    # (Requer revisão do conteúdo)
│   ├── uploads.py
│   ├── uso_ia.py
│   └── web_enrichment.py
├── services/             # Lógica de negócios e integrações.
│   ├── init.py
│   ├── file_processing_service.py
│   ├── ia_generation_service.py
│   ├── limit_service.py
│   └── web_data_extractor_service.py
├── templates/            # Templates HTML (ex: para emails).
│   └── password_reset_email.html
├── init.py
├── auth.py               # Lógica de autenticação, tokens, OAuth.
├── crud.py               # Funções de acesso ao banco de dados (CRUD).
├── database.py           # Configuração da conexão com o banco de dados.
├── main.py               # Ponto de entrada da aplicação FastAPI.
├── models.py             # Definições dos modelos SQLAlchemy.
└── schemas.py            # Definições dos schemas Pydantic.


## ⚙️ Configuração e Execução

Siga os passos abaixo para configurar e executar o backend localmente.

**1. Pré-requisitos:**

* Python 3.8+
* PostgreSQL (servidor em execução)
* Servidor SMTP (para funcionalidade de email, como recuperação de senha)
* Chaves de API:
    * OpenAI API Key
    * Google Custom Search Engine (CSE) API Key e CSE ID
    * Google OAuth Client ID e Client Secret
    * Facebook OAuth Client ID e Client Secret

**2. Clonar o Repositório (se aplicável):**

```bash
git clone <url-do-seu-repositorio>
cd <PROJECT_ROOT_DIRECTORY_NAME> # Navegue até a raiz do projeto TDAI
3. Criar e Ativar um Ambiente Virtual:

Recomendado para isolar as dependências do projeto. Execute na raiz do projeto (<PROJECT_ROOT_DIRECTORY_NAME>):

Bash

python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows
4. Instalar Dependências:


Todas as bibliotecas necessárias para o backend já estão listadas em
`requirements-backend.txt`. Execute na raiz do projeto:

```bash
pip install -r requirements-backend.txt
```

Bash

Já existe um arquivo requirements-backend.txt com as principais bibliotecas.
Execute na raiz do projeto:

Bash

pip install -r requirements-backend.txt
playwright install


5. Configurar Variáveis de Ambiente:

As configurações da aplicação são carregadas a partir de um arquivo .env localizado na raiz do projeto (<PROJECT_ROOT_DIRECTORY_NAME>/.env).

Crie um arquivo chamado .env na raiz do projeto.

**Nunca coloque senhas ou chaves reais diretamente neste arquivo.** Use variáveis de ambiente ou um gerenciador de segredos para armazenar credenciais com segurança.

Você precisará adicionar as seguintes variáveis (um arquivo .env.example seria ideal para listar todas as chaves necessárias):

Snippet de código

# Backend/core/config.py espera estas variáveis
DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" # Ex: postgresql://postgres:password@localhost:5432/tdai_db
SECRET_KEY="sua_chave_secreta_super_forte_aqui" # Importante para JWT

REFRESH_SECRET_KEY="change-me"
REFRESH_SECRET_KEY="sua_chave_refresh_super_forte_aqui"

ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# OpenAI
OPENAI_API_KEY="sk-..."

# Google OAuth
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
GOOGLE_REDIRECT_URI="http://localhost:8000/auth/google/callback" # Ajuste se seu backend rodar em outra porta

# Facebook OAuth
FACEBOOK_CLIENT_ID="..."
FACEBOOK_CLIENT_SECRET="..."
FACEBOOK_REDIRECT_URI="http://localhost:8000/auth/facebook/callback" # Ajuste se necessário

# Google Search API (Custom Search Engine)
GOOGLE_CSE_API_KEY="..."
GOOGLE_CSE_ID="..."

# Configurações de Email (FastAPI-Mail)
MAIL_USERNAME="..."
MAIL_PASSWORD="..."
MAIL_FROM="seu_email@example.com"
MAIL_PORT=587
MAIL_SERVER="smtp.example.com"
MAIL_FROM_NAME="Equipe TDAI"
MAIL_STARTTLS="True" # True ou False
MAIL_SSL_TLS="False"  # True ou False
USE_CREDENTIALS="True" # True ou False
VALIDATE_CERTS="True"  # True ou False

# URL do Frontend (para links em emails, etc.)
FRONTEND_URL="http://localhost:5173" # Ou a porta do seu frontend Vite/React

# Opcional: para o usuário admin padrão criado no startup
ADMIN_EMAIL="<ADMIN_EMAIL>"
ADMIN_PASSWORD="<ADMIN_PASSWORD>"
Preencha os valores corretos para cada variável. O arquivo Backend/core/config.py define como essas variáveis são lidas.

6. Migrações do Banco de Dados:

Este projeto utiliza SQLAlchemy.

Se estiver usando Alembic (recomendado para produção): Certifique-se de que o Alembic está configurado (normalmente com alembic.ini e uma pasta alembic/ dentro de Backend/). Execute as migrações:
Bash

cd Backend  # Navegue para a pasta Backend onde alembic.ini geralmente reside
alembic upgrade head
cd ..     # Volte para a raiz do projeto
Se NÃO estiver usando Alembic: A linha models.Base.metadata.create_all(bind=engine) em Backend/main.py (atualmente comentada) precisaria ser descomentada para criar as tabelas automaticamente ao iniciar a aplicação. No entanto, isso não é recomendado para gerenciamento de schema a longo prazo.
7. Executar a Aplicação Backend:

Na raiz do projeto (<PROJECT_ROOT_DIRECTORY_NAME>), execute o script run_backend.py:

Bash

python run_backend.py
Este script (run_backend.py) irá configurar o ambiente e iniciar o servidor Uvicorn.
A API estará disponível em http://localhost:8000 e a documentação interativa (Swagger UI) em http://localhost:8000/docs.

📝 Endpoints da API
A API possui diversos endpoints para gerenciar os recursos. A melhor forma de explorá-los é através da documentação interativa gerada pelo FastAPI:

Documentação Swagger UI: http://localhost:8000/docs
Documentação ReDoc: http://localhost:8000/redoc