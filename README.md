# TDAI – Plataforma Inteligente de Enriquecimento e Geração de Conteúdo para Catálogos

> **Autor:** Julio Cesar Barizon Montes
> **Licença:** Todos os direitos reservados

---

## 🚀 Visão Geral

O **TDAI** é uma plataforma SaaS de automação e inteligência artificial para catálogos de produtos. O sistema facilita o cadastro, enriquecimento e geração de títulos e descrições para grandes listas de produtos, reduzindo trabalho manual e elevando o padrão de qualidade do conteúdo – pronto para marketplaces, e-commerce e operações B2B.

* Upload em massa (planilhas, PDFs)
* Enriquecimento automático via web scraping & IA
* Geração de títulos/descritivos prontos para venda
* Controle total de fornecedores, tipos e atributos
* Administração de planos, permissões, créditos e limites
* Painéis de analytics e controle de uso de IA

---

## 📑 Sumário

* [Principais Funcionalidades](#principais-funcionalidades)
* [Arquitetura e Estrutura de Pastas](#arquitetura-e-estrutura-de-pastas)
* [Fluxo de Uso](#fluxo-de-uso)
* [Guia de Instalação Rápida](#guia-de-instalação-rápida)
* [Variáveis de Ambiente – Exemplo ](#variáveis-de-ambiente--exemplo-env)[`.env`](#variáveis-de-ambiente--exemplo-env)
* [Comandos Úteis](#comandos-úteis)
* [Roadmap e Futuro](#roadmap-e-futuro)
* [Segurança e Boas Práticas](#segurança-e-boas-práticas)
* [FAQ](#faq)
* [Licença](#licença)

---

## 🏆 Principais Funcionalidades

* **Autenticação & Segurança**
  Login por senha, Google e Facebook (OAuth 2.0). Controle de roles, planos, expiração de sessão e recuperação de senha via email.

* **Cadastro Ágil de Produtos**
  Cadastro manual, por planilha (CSV/XLSX) ou PDF, com extração automática de dados.

* **Enriquecimento Web Automático**
  Pesquisa informações relevantes em sites, catálogos, Google Search, fornecedores – com scraping e extração inteligente de texto/atributos.

* **Geração de Conteúdo com IA**
  Geração automática de títulos e descrições de alta qualidade usando OpenAI. Fluxo auditável, histórico por usuário/produto.

* **Gestão Completa de Fornecedores**
  Cadastro, edição, associação a produtos, controle de dados e relacionamentos.

* **Tipos de Produto e Atributos Dinâmicos**
  Permite criar templates para diferentes categorias (ex: pneus, autopeças, eletrônicos), com atributos customizáveis.

* **Controle de Planos & Créditos**
  Definição de limites de uso por plano, créditos de IA, bloqueio automático ao atingir limites.

* **Dashboard & Analytics**
  Relatórios de uso, consumo de IA, produtos enriquecidos, atividade de usuários/admin.

* **Frontend Moderno e Responsivo**
  Interface em React com navegação intuitiva, feedback visual, páginas protegidas e integrações em tempo real.

---

## 🗂️ Arquitetura e Estrutura de Pastas

```
TDAI/
│
├── Backend/                 # API, banco, lógica, integrações, serviços
│   ├── alembic/             # Migrations do banco (Alembic)
│   ├── core/                # Configurações, email, segurança
│   ├── routers/             # Endpoints REST da aplicação
│   ├── services/            # Lógica de negócio: IA, scraping, limites, arquivos
│   ├── templates/           # Templates de emails
│   ├── models.py            # Modelos ORM (banco)
│   ├── schemas.py           # Schemas Pydantic (API)
│   ├── main.py              # Inicialização FastAPI
│   ├── auth.py, crud.py, database.py, ...
│
├── Frontend/
│   └── app/
│       ├── public/          # Assets estáticos (SVG, favicon, etc)
│       ├── src/
│       │   ├── components/  # Componentes React reutilizáveis
│       │   ├── pages/       # Páginas de navegação
│       │   ├── App.jsx      # Raiz da aplicação
│       │   ├── main.jsx     # Entry point React
│       │   └── ...          # Outros helpers, contextos, assets
│       ├── package.json, vite.config.js, ...
│
├── .env                     # Variáveis de ambiente (NÃO versionar!)
├── run_backend.py           # Inicia API (FastAPI/Uvicorn)
├── README.md                # Este arquivo
└── TDAI.pdf                 # Protótipo, especificação e wireframes
```

---

## 🔄 Fluxo de Uso

1. **Login/Cadastro**

   * Cadastro via email/senha ou social login (Google/Facebook)
2. **Cadastro de Fornecedores/Produtos**

   * Manual, upload de planilhas/PDF ou integração
3. **Enriquecimento Web**

   * Seleção de produtos → enriquecimento automático (scraping, busca Google, etc)
4. **Geração IA**

   * Seleção de produto → geração de título/descrição por IA
5. **Download/Exportação**

   * Resultados podem ser copiados ou exportados para planilha
6. **Dashboard/Admin**

   * Relatórios, analytics, limites, upgrade de plano

---

## ⚡ Guia de Instalação Rápida

### 1. **Pré-requisitos**

* Python 3.8+
* Node.js 18+
* PostgreSQL 12+
* Git
* Navegadores Playwright (para scraping):
  `playwright install`
* Chaves de API: OpenAI, Google Search, SMTP
* Variáveis no arquivo `.env`

---

### 2. **Clonar o Projeto**

```sh
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_PROJETO>
```

---

### 3. **Configuração do Backend**

```sh
python -m venv venv
source venv/bin/activate    # Ou .\venv\Scripts\activate no Windows
pip install -r Backend/requirements.txt
cd Backend
alembic upgrade head        # Cria as tabelas do banco
cd ..
python run_backend.py       # Inicia o backend (http://localhost:8000)
```

---

### 4. **Configuração do Frontend**

```sh
cd Frontend/app
npm install
npm run dev                 # Roda o frontend em http://localhost:5173
```

---

### 5. **Acesse a Plataforma**

* **Frontend:**
  [http://localhost:5173](http://localhost:5173)

* **Documentação API:**
  [http://localhost:8000/docs](http://localhost:8000/docs)
  [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## ⚙️ Variáveis de Ambiente – Exemplo `.env`

```
# Banco de Dados
DATABASE_URL="postgresql://usuario:senha@localhost:5432/tdai_db"

# Segurança
SECRET_KEY="sua_chave_forte"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# OpenAI
OPENAI_API_KEY="sk-..."

# Google Search API
GOOGLE_CSE_ID="..."
GOOGLE_CSE_API_KEY="..."

# SMTP/Email
SMTP_SERVER="smtp.seuprovedor.com"
SMTP_PORT=587
SMTP_USER="seu@email.com"
SMTP_PASSWORD="senha"
EMAIL_FROM="TDAI Platform <nao-responda@tdai.com>"

# Frontend
FRONTEND_URL="http://localhost:5173"

# OAuth2 (Google/Facebook)
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
FACEBOOK_CLIENT_ID="..."
FACEBOOK_CLIENT_SECRET="..."

# Admin padrão
ADMIN_EMAIL="admin@email.com"
ADMIN_PASSWORD="adminpassword"
```

> ⚠️ **Nunca suba este arquivo para o git!**

---

## 🛠️ Comandos Úteis

* **Iniciar Backend:**
  `python run_backend.py`

* **Rodar Migrations:**
  `cd Backend && alembic upgrade head`

* **Instalar navegadores Playwright:**
  `playwright install`

* **Iniciar Frontend:**
  `npm run dev` (na pasta `Frontend/app`)

* **Explorar Endpoints API:**

  * `/produtos/`, `/fornecedores/`, `/uploads/`, `/generation/`, `/web-enrichment/`, `/uso_ia/` etc.
  * Veja todos em `/docs`

---

## 📈 Roadmap e Futuro

*

---

## 🔒 Segurança e Boas Práticas

* Senhas hasheadas com bcrypt
* JWT seguro para sessões
* OAuth 2.0 seguindo padrões Google/Facebook
* Validação de entrada rigorosa (Pydantic)
* Controle de permissões e roles
* Variáveis sensíveis fora do versionamento
* Respeito a robots.txt nos crawlers
* Atualização frequente de dependências

---

## 💬 FAQ

**P:** Posso usar outro banco de dados?
**R:** O suporte principal é para PostgreSQL, mas há fallback para SQLite em dev.

**P:** Como funciona o limite de IA?
**R:** Cada plano tem créditos e limites definidos; ao atingir, novos enriquecimentos/gerações são bloqueados.

**P:** Como expandir os tipos de produto?
**R:** Basta cadastrar novos templates de atributos pelo frontend ou via API.

**P:** Posso customizar prompts de IA?
**R:** Futuro roadmap prevê templates dinâmicos avançados.

---

## 📜 Licença

**Todos os direitos reservados.**
Julio Cesar Barizon Montes

---

> **Dúvidas, sugestões ou parcerias?**
> Entre em contato pelo repositório ou diretamente com o autor.
