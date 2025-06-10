# CatalogAI – Plataforma Inteligente de Enriquecimento e Geração de Conteúdo para Catálogos

> **Autor:** Julio Cesar Barizon Montes
> **Licença:** [MIT](LICENSE)

---

## 🚀 Visão Geral

O **CatalogAI** é uma plataforma SaaS de automação e inteligência artificial para catálogos de produtos. O sistema facilita o cadastro, enriquecimento e geração de títulos e descrições para grandes listas de produtos, reduzindo trabalho manual e elevando o padrão de qualidade do conteúdo – pronto para marketplaces, e-commerce e operações B2B.

* Upload em massa (planilhas, PDFs)
* Enriquecimento automático via web scraping & IA
* Geração de títulos/descritivos prontos para venda
* Controle total de fornecedores, tipos e atributos
* Administração de planos, permissões, créditos e limites
* Painéis de analytics e controle de uso de IA
* Registro histórico de ações realizadas e execuções de IA

---

## 📑 Sumário

* [Principais Funcionalidades](#principais-funcionalidades)
* [Arquitetura e Estrutura de Pastas](#arquitetura-e-estrutura-de-pastas)
* [Fluxo de Uso](#fluxo-de-uso)
* [Guia de Instalação Rápida](#guia-de-instalação-rápida)
* [Variáveis de Ambiente](#variáveis-de-ambiente)
* [Comandos Úteis](#comandos-úteis)
* [Testes](#testes)
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
CatalogAI-0525-Dev/
├── .gitignore
├── README.md
├── README.txt
├── CatalogAI.pdf
├── run_backend.py
├── Backend/
│   ├── __init__.py
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── README
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 522dce3cd6aa_initial_database_schema.py
│   ├── auth.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── email_utils.py
│   │   └── security.py
│   ├── crud.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── admin_analytics.py
│   │   ├── auth_utils.py
│   │   ├── fornecedores.py
│   │   ├── generation.py
│   │   ├── password_recovery.py
│   │   ├── product_types.py
│   │   ├── produtos.py
│   │   ├── social_auth.py
│   │   ├── uploads.py
│   │   ├── uso_ia.py
│   │   └── web_enrichment.py
│   ├── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_processing_service.py
│   │   ├── ia_generation_service.py
│   │   ├── limit_service.py
│   │   └── web_data_extractor_service.py
│   ├── templates/
│   │   └── password_reset_email.html
├── Frontend/
│   └── app/
│       ├── README.md
│       ├── eslint.config.js
│       ├── index.html
│       ├── package-lock.json
│       ├── package.json
│       ├── public/
│       │   └── vite.svg
│       ├── src/
│       │   ├── App.css
│       │   ├── App.jsx
│       │   ├── assets/
│       │   │   ├── react.svg
│       │   │   └── vite.svg
│       │   ├── common/
│       │   │   ├── Modal.jsx
│       │   │   └── PaginationControls.jsx
│       │   ├── components/
│       │   │   ├── AttributeTemplateList.jsx
│       │   │   ├── AttributeTemplateModal.jsx
│       │   │   ├── EditFornecedorModal.jsx
│       │   │   ├── FornecedorTable.jsx
│       │   │   ├── MainLayout.jsx
│       │   │   ├── NewFornecedorModal.jsx
│       │   │   ├── NewProductModal.jsx
│       │   │   ├── ProductEditModal.jsx
│       │   │   ├── ProductTable.jsx
│       │   │   ├── ProtectedRoute.jsx
│       │   │   ├── Sidebar.jsx
│       │   │   └── Topbar.jsx
│       │   ├── index.css
│       │   ├── main.jsx
│       │   ├── pages/
│       │   │   └── (suas páginas específicas, ex: Dashboard, Login, etc)
│       │   └── produtos/
│       │       └── shared/
│       │           └── AttributeField.jsx
│       ├── vite.config.js
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
* Chaves de API: OpenAI, Google Search, serviço de e-mail (SMTP)
* Copie o arquivo `.env.example` para `.env` e ajuste os valores

---

### 2. **Clonar o Projeto**

```sh
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_PROJETO>
```

---

### 3. **Configuração do Backend**

As dependências Python necessárias estão listadas em `requirements-backend.txt`.

```sh
python -m venv venv
source venv/bin/activate    # Ou .\venv\Scripts\activate no Windows
pip install -r requirements-backend.txt   # dependências fixas do backend
cd Backend
alembic upgrade head        # Cria/atualiza tabelas, incluindo RegistroHistorico
cd ..
python run_backend.py       # Inicia o backend (http://localhost:8000)
```

Após a primeira execução, o backend cria automaticamente um usuário administrador
e um **produto de exemplo**. Utilize as credenciais definidas em `.env` para
acessar a plataforma e visualizar esse item inicial.

---

### 4. **Configuração do Frontend**

Siga os passos abaixo para rodar a interface em React.
Caso o `npm install` retorne o erro `ERESOLVE` (conflito de *peer dependencies*),
execute `npm install --legacy-peer-deps` ou atualize o `package.json` para
versões compatíveis e tente novamente.

```sh
cd Frontend/app
npm install
# Certifique-se de que as dependências de desenvolvimento (como @eslint/js)
# foram instaladas. Elas são necessárias para o comando de lint.
npm run lint            # Opcional: verifica padrões de código
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


## ⚙️ Variáveis de Ambiente

Todas as variáveis necessárias para o backend e o frontend estão documentadas em [`.env.example`](./.env.example).
Copie este arquivo para `.env` e preencha com seus valores antes de iniciar a aplicação.

### 6. **Testes**

```sh
# Backend
pip install -r requirements-backend.txt
pytest

# Frontend
cd Frontend/app
npm test
```

---

## ⚙️ Variáveis de Ambiente – Exemplo `.env`

```
# Banco de Dados
DATABASE_URL="postgresql://usuario:senha@localhost:5432/catalogai_db"
SQLITE_DB_FILE="catalogai_app.db"  # usado automaticamente se DATABASE_URL estiver ausente

# Segurança
SECRET_KEY="sua_chave_forte"

REFRESH_SECRET_KEY="sua_chave_refresh_forte"

ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# OpenAI
OPENAI_API_KEY="sk-..."
# Google Gemini API
GOOGLE_GEMINI_API_KEY="..."

# Google Search API
GOOGLE_CSE_ID="..."
GOOGLE_CSE_API_KEY="..."

# Email
MAIL_USERNAME=""
MAIL_PASSWORD=""
MAIL_FROM=""
MAIL_PORT=587
MAIL_SERVER="smtp.example.com"
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
MAIL_FROM_NAME="CatalogAI Platform"

# Frontend
FRONTEND_URL="http://localhost:5173"

# OAuth2 (Google/Facebook)
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
FACEBOOK_CLIENT_ID="..."
FACEBOOK_CLIENT_SECRET="..."

# Custos de IA
CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI=1

# Admin padrão
ADMIN_EMAIL="<ADMIN_EMAIL>"
ADMIN_PASSWORD="<ADMIN_PASSWORD>"
FIRST_SUPERUSER_EMAIL="<FIRST_SUPERUSER_EMAIL>"
FIRST_SUPERUSER_PASSWORD="<FIRST_SUPERUSER_PASSWORD>"
```

Se `DATABASE_URL` não estiver definido, o backend utilizará automaticamente
SQLite, criando o arquivo no caminho especificado por `SQLITE_DB_FILE`. Caso
você não tenha PostgreSQL disponível, remova ou comente a variável
`DATABASE_URL` ou ajuste o caminho do arquivo SQLite conforme necessário.

> ⚠️ **Nunca suba arquivos `.env` com dados sensíveis para o git!**
> Configure senhas e chaves reais via variáveis de ambiente ou um gerenciador de segredos seguro.

---

## 🔍 Verificando Credenciais do PostgreSQL

Certifique-se de que a senha definida em `DATABASE_URL` está correta e que o
usuário informado possui a mesma senha cadastrada no PostgreSQL. Você pode testar
a conexão executando:

```sh
psql -h <host> -U <usuario> -W
```

Se a conexão falhar, ajuste `DATABASE_URL` ou atualize a senha do usuário para
que coincidam.

## 🛠️ Comandos Úteis

* **Iniciar Backend:**
  `python run_backend.py`

* **Rodar Migrations:**
  `cd Backend && alembic upgrade head`  # aplica migrações, inclusive a tabela RegistroHistorico

* **Instalar navegadores Playwright:**
  `playwright install`

* **Iniciar Frontend:**
  `npm run dev` (na pasta `Frontend/app`)
* **Verificar código com ESLint:**
  `npm run lint` (exige dependências de desenvolvimento instaladas)

* **Explorar Endpoints API:**

  * `/produtos/`, `/fornecedores/`, `/uploads/`, `/generation/`, `/web-enrichment/`, `/uso_ia/`, `/historico/` etc.
  * Veja todos em `/docs`
  * Para listar os tipos de ações suportados, consulte `GET /historico/tipos`

### Exemplo de uso no Frontend

```javascript
import usoIAService from './services/usoIAService';

// Buscar histórico de IA do usuário logado
const historico = await usoIAService.getMeuHistoricoUsoIA({ skip: 0, limit: 10 });
console.log(historico.items);
```

---

## 🧪 Testes

Os testes do backend dependem das bibliotecas listadas em `requirements-backend.txt`. Para executá-los:

```sh
pip install -r requirements-backend.txt
pytest
```

---

## 📈 Roadmap e Futuro

* [ ] Geração de variações para múltiplos marketplaces
* [ ] Enriquecimento com análise de imagem (background, alt-text, etc)
* [ ] Integração com ERPs e publicadores externos
* [ ] Automação por agentes multi-IA
* [ ] Personalização de conteúdo por persona/segmento
* [ ] Sistema de feedback e aprendizado contínuo
* [ ] Templates dinâmicos de prompt

---

## ✅ Conclusão da Fase Atual

Esta etapa inclui avanços importantes de qualidade:

* Implementados testes unitários e de integração (pasta `tests/`).
* Estilos revistos no frontend para aderência ao protótipo.
* Ajustes de performance e usabilidade documentados nesta versão.

### Melhorias de Desempenho e Usabilidade

* Utilização de variáveis CSS para acelerar o carregamento de estilos.
* Layout do sidebar unificado, garantindo navegação mais consistente.

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

Distribuído sob os termos da [licença MIT](LICENSE).

---

> **Dúvidas, sugestões ou parcerias?**
> Entre em contato pelo repositório ou diretamente com o autor.
