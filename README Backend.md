# Documentação Completa de Funções — Backend

---

## .gitignore

* **Sem funções**: Arquivo de configuração que define padrões de arquivos e pastas a serem ignorados pelo Git.

## README.md

* **Sem funções**: Documentação principal do projeto.

## README.txt

* **Sem funções**: Versão antiga da documentação.

## CatalogAI.pdf

* **Sem funções**: Documento visual/protótipo do sistema.

## run\_backend.py

* **Função principal**: Executa o servidor FastAPI/Uvicorn utilizando configurações do projeto.

## Dependência para conversão de PDF

* Para gerar previews de PDF é necessário instalar o pacote `poppler-utils` (ex.: `apt install poppler-utils`). Sem ele o backend não conseguirá converter PDFs em imagens, e o preview de PDF não será gerado.

### Poppler no Windows

Para usuários do Windows, instale o Poppler via Chocolatey (`choco install poppler`) ou baixe os binários em <https://github.com/oschwartz10612/poppler-windows/releases>.
Após a instalação, adicione o diretório que contém `pdftoppm.exe` ao `PATH` ou defina a variável `POPPLER_PATH`. A função `pdf_pages_to_images` lê essa variável se o executável não estiver no `PATH`.

---

## Backend/**init**.py

* **Sem funções**: Marca o diretório como módulo Python.

## Backend/alembic.ini

* **Sem funções**: Configuração do Alembic para migrações de banco de dados.

## Backend/alembic/README

* **Sem funções**: Orientações de uso do Alembic.

## Backend/alembic/env.py

* `run_migrations_online()`: Executa migrações conectando ao banco.
* `run_migrations_offline()`: Executa migrações em modo offline.
* **Outras funções utilitárias**: Inicialização de contexto, importação de models, configuração de paths e de logging.

## Backend/alembic/script.py.mako

* **Sem funções**: Template para scripts de migração.

## Backend/alembic/versions/522dce3cd6aa\_initial\_database\_schema.py

* `upgrade()`: Cria todas as tabelas e constraints necessárias.
* `downgrade()`: Remove as tabelas criadas na migration.

* Nova migration cria a tabela `registros_historico` para armazenar ações.

---

## Backend/auth.py

* `authenticate_user(db, email, password)`: Verifica se o email e senha informados são válidos.
* `get_user(db, user_id)`: Busca um usuário pelo ID.
* `login_for_access_token(form_data, db)`: Realiza o login, gera e retorna um token JWT.
* `register(user_data, db)`: Registra um novo usuário no banco de dados.
* `forgot_password(email, db)`: Inicia o processo de redefinição de senha, gerando token e enviando email.
* `reset_password(token, new_password, db)`: Atualiza a senha do usuário usando o token de reset.
* `verify_token(token, db)`: Valida o token de redefinição de senha.

---

## Backend/core/**init**.py

* **Sem funções**: Marca o diretório como módulo Python.

## Backend/core/config.py

* `class Settings(BaseSettings)`: Classe principal de configuração. Carrega variáveis do `.env` para todo o projeto.
* `get_settings()`: Retorna a instância de `Settings`.

## Backend/core/email\_utils.py

* `send_reset_password_email(email_to, user_name, reset_link)`: Envia email de redefinição de senha ao usuário.
* `send_welcome_email(email_to, user_name)`: Envia email de boas-vindas a um novo usuário.

## Backend/core/security.py

* `get_password_hash(password)`: Gera um hash seguro para a senha.
* `verify_password(plain_password, hashed_password)`: Compara senha em texto puro com o hash.
* `create_access_token(data, expires_delta)`: Cria JWT (token de acesso) com payload e expiração.
* `decode_access_token(token)`: Decodifica e valida um JWT recebido.
* `create_refresh_token(data)`: Gera refresh token de longa duração.
* `verify_token(token)`: Verifica se o token JWT é válido e não expirou.
* `get_random_secret_key()`: Gera string aleatória para ser utilizada como chave secreta.
* `generate_salt()`: Cria um salt randômico para aprimorar a segurança das senhas.

---

## Backend/crud.py

* `get_user_by_email(db, email)`: Busca usuário por email.
* `get_user_by_id(db, user_id)`: Busca usuário pelo ID.
* `create_user(db, user)`: Cria um novo usuário.
* `update_user(db, user_id, user_update)`: Atualiza os dados de um usuário.
* `delete_user(db, user_id)`: Remove um usuário do banco.
* `list_users(db)`: Lista todos os usuários cadastrados.
* `get_supplier_by_id(db, supplier_id)`: Busca fornecedor pelo ID.
* `get_supplier_by_cnpj(db, cnpj)`: Busca fornecedor pelo CNPJ.
* `create_supplier(db, fornecedor)`: Cria novo fornecedor.
* `update_supplier(db, id, update_data)`: Atualiza dados do fornecedor.
* `delete_supplier(db, id)`: Remove fornecedor do banco.
* `list_suppliers(db)`: Lista todos os fornecedores.
* `get_product_by_id(db, id)`: Busca produto pelo ID.
* `create_product(db, produto)`: Cria novo produto.
* `update_product(db, id, update_data)`: Atualiza dados do produto.
* `delete_product(db, id)`: Remove produto do banco.
* `list_products(db, filters)`: Lista produtos, com filtros opcionais.
* `get_plan_by_id(db, id)`: Busca plano pelo ID.
* `create_plan(db, plan)`: Cria um novo plano.
* `update_plan(db, id, update_data)`: Atualiza dados do plano.
* `delete_plan(db, id)`: Remove plano do banco.
* `list_plans(db)`: Lista todos os planos cadastrados.
* `get_role_by_id(db, id)`: Busca uma role pelo ID.
* `create_role(db, role)`: Cria uma nova role.
* `update_role(db, id, update_data)`: Atualiza dados da role.
* `delete_role(db, id)`: Remove role do banco.
* `list_roles(db)`: Lista todas as roles.
* `get_ia_usage_by_id(db, id)`: Busca registro de uso de IA pelo ID.
* `create_ia_usage(db, usage)`: Cria novo registro de uso de IA.
* `update_ia_usage(db, id, update_data)`: Atualiza uso de IA.
* `delete_ia_usage(db, id)`: Remove uso de IA do banco.
* `list_ia_usages(db, user_id=None)`: Lista registros de uso de IA.

---

## Backend/database.py

* `get_db()`: Gerador de sessão do banco, usado em dependências do FastAPI.
* `init_db()`: Inicializa o banco de dados, criando tabelas caso não existam.

---

## Backend/main.py

* `startup_event()`: Executa ao iniciar o app, criando admin default e recursos essenciais.
* (Instancia o FastAPI e inclui todos os routers, middlewares, handlers de eventos.)

---

## Backend/models.py

* `class User(Base)`: Modelo ORM do usuário.

  * **Atributos**: id, nome, email, senha\_hash, role, ativo, criado\_em, etc.
  * `__repr__()`: Retorna representação textual do usuário.
* `class Produto(Base)`: Modelo ORM de produto.

  * **Atributos**: id, nome, fornecedor\_id, atributos, enriquecido, data.
  * `__repr__()`: Retorna representação textual do produto.
* `class Fornecedor(Base)`: Modelo ORM de fornecedor.

  * **Atributos**: id, nome, cnpj, email, etc.
  * `__repr__()`: Retorna representação textual do fornecedor.
* `class Plan(Base)`: Modelo ORM de plano.

  * **Atributos**: id, nome, limites, preço, etc.
  * `__repr__()`: Retorna representação textual do plano.
* `class Role(Base)`: Modelo ORM de perfil de usuário.

  * **Atributos**: id, nome, permissões, etc.
  * `__repr__()`: Retorna representação textual da role.
* `class IAUsage(Base)`: Modelo ORM do uso de IA.

  * **Atributos**: id, user\_id, tipo, tokens, data.
  * `__repr__()`: Retorna representação textual do uso de IA.
* `class RegistroHistorico(Base)`: Armazena ações realizadas e execuções de IA.

  * **Atributos**: id, user_id, produto_id, tipo_acao, detalhes e timestamps.
  * `__repr__()`: Retorna representação textual do registro.


---

## Backend/routers/**init**.py

* **Sem funções**: Marca o diretório como módulo Python.

## Backend/routers/admin\_analytics.py

* `get_analytics_data()`: Retorna métricas e estatísticas globais do sistema (produtos criados, uso de IA, usuários ativos, planos ativos).

## Backend/routers/auth\_utils.py

* `get_current_user()`: Recupera o usuário autenticado pelo token JWT, usado em Depends.
* `get_current_active_user()`: Checa se o usuário está ativo (ativo=True).

## Backend/routers/fornecedores.py

* `create_supplier(fornecedor: FornecedorCreate, db: Session)`: Cria novo fornecedor.
* `list_suppliers(skip: int = 0, limit: int = 100, db: Session)`: Lista fornecedores com paginação (campo `page` inicia em 1).
* `get_supplier(supplier_id: int, db: Session)`: Busca fornecedor pelo ID.
* `update_supplier(supplier_id: int, update: FornecedorUpdate, db: Session)`: Atualiza fornecedor.
* `delete_supplier(supplier_id: int, db: Session)`: Remove fornecedor.

## Backend/routers/generation.py

* `generate_product_content(product_id: int, db: Session)`: Gera título/descrição para produto via IA.
* `regenerate_content(product_id: int, db: Session)`: Refaz geração de conteúdo IA para produto.

## Backend/routers/password\_recovery.py

* `request_password_reset(email: str, db: Session)`: Envia email de reset de senha.
* `validate_reset_token(token: str, db: Session)`: Valida token de reset recebido.
* `set_new_password(token: str, new_password: str, db: Session)`: Altera a senha do usuário.

## Backend/routers/product\_types.py

* `create_type(tipo: TipoCreate, db: Session)`: Cria tipo/template de produto.
* `list_types(skip: int = 0, limit: int = 100, db: Session)`: Lista tipos/templates de produto.
* `get_type(type_id: int, db: Session)`: Busca tipo por ID.
* `update_type(type_id: int, update: TipoUpdate, db: Session)`: Atualiza tipo/template.
* `delete_type(type_id: int, db: Session)`: Remove tipo/template.

## Backend/routers/produtos.py

* `create_product(produto: ProdutoCreate, db: Session)`: Cria novo produto.
* `list_products(skip: int = 0, limit: int = 100, db: Session)`: Lista produtos cadastrados.
* `get_product(product_id: int, db: Session)`: Busca produto pelo ID.
* `update_product(product_id: int, update: ProdutoUpdate, db: Session)`: Atualiza produto.
* `delete_product(product_id: int, db: Session)`: Remove produto.
* `list_catalog_import_files(fornecedor_id: Optional[int], skip: int = 0, limit: int = 100, db: Session)`: Lista arquivos de importação de catálogos do usuário.
* `importar_catalogo_preview(file: UploadFile, fornecedor_id: Optional[int], page_count: int, start_page: int, db: Session)`: Envia um arquivo e retorna apenas o número de páginas e imagens para visualização, sem extrair cabeçalhos ou amostras. O parâmetro `start_page` define a página inicial usada para gerar as imagens de preview do PDF.
* `importar_catalogo_fornecedor(fornecedor_id: int, file: UploadFile, mapeamento_colunas_usuario: Optional[str], db: Session)`: Importa catálogo e cria produtos imediatamente.
* `importar_catalogo_finalizar(file_id: int, product_type_id: int, fornecedor_id: int, mapping: Optional[dict], db: Session)`: Processa em background um arquivo já enviado.
* `importar_catalogo_status(file_id: int, db: Session)`: Consulta o status do processamento do catálogo.
* `selecionar_regiao(file_id: int, page: int, bbox: List[float], db: Session)`: Processa região selecionada de um PDF e retorna produtos detectados.

## Backend/routers/social\_auth.py

* `login_google(token: str, db: Session)`: Login/cadastro via Google OAuth2.
* `login_facebook(token: str, db: Session)`: Login/cadastro via Facebook OAuth2.

## Backend/routers/uploads.py

* `upload_file(file: UploadFile, db: Session)`: Recebe e processa arquivo de upload.
* `get_upload_status(upload_id: int, db: Session)`: Consulta status de upload/processamento.

## Backend/routers/uso\_ia.py

* `get_ia_usage(user_id: int, db: Session)`: Retorna uso de IA do usuário.
* `get_ia_usage_admin(db: Session)`: Retorna relatório geral de uso IA.

## Backend/routers/historico.py

* `list_historico(...)`: Lista ações salvas no RegistroHistorico por usuário.
* `get_tipos_acao()`: Retorna os valores do enum TipoAcaoEnum.

## Backend/routers/web\_enrichment.py

* `enrich_product(product_id: int, db: Session)`: Executa scraping/enriquecimento web do produto.
* `get_enrichment_status(enrichment_id: int, db: Session)`: Consulta status do enriquecimento web.

---

## Backend/schemas.py

* **Várias classes Pydantic** para cada entidade (User, Produto, Fornecedor, Plano, Role, IAUsage, etc), contendo métodos de validação, exemplos de campos e enums.
---
## Backend/services/**init**.py

* **Sem funções**: Marca o diretório como módulo Python.

## Backend/services/file\_processing\_service.py

* `process_uploaded_file(file, db)`: Detecta tipo do arquivo e processa conteúdo em lote.
* `parse_csv(file)`: Lê CSV e converte em lista de dicts.
* `parse_xlsx(file)`: Lê XLSX e converte em lista de dicts.
* `parse_pdf(file)`: Extrai dados estruturados de PDF.
* `validate_row(row)`: Valida campos obrigatórios de cada linha.
* `create_products_from_rows(rows, db)`: Cria produtos a partir dos dados validados.
* `log_processing_error(error)`: Registra erros durante o processamento.

## Backend/services/ia\_generation\_service.py

* `generate_content_with_ia(product, prompt_template)`: Monta prompt, chama OpenAI, recebe resposta.
* `save_ia_result(product_id, result, tokens_used, db)`: Armazena texto gerado pela IA e tokens usados.
* `retry_generation(product_id, db)`: Refaz geração caso necessário.

## Backend/services/limit\_service.py

* `check_and_update_limits(user, action, db)`: Consulta e atualiza limites de uso do usuário.
* `get_user_limits(user, db)`: Retorna limites atuais do usuário.
* `block_usage(user, action, db)`: Bloqueia uso se limite for atingido.


## Backend/services/web\_data\_extractor\_service.py

* `enrich_product_with_web(product, db)`: Realiza scraping e busca Google.
* `scrape_website(url)`: Scraping básico de um site.
* `extract_with_trafilatura(html)`: Extrai texto de HTML com Trafilatura.
* `extract_metadata_with_extruct(html)`: Extrai metadados de páginas HTML.
* `normalize_scraped_data(data)`: Padroniza dados coletados.
* `update_product_with_enriched_data(product, enriched_data, db)`: Atualiza o produto com dados externos.

---

## Backend/templates/password\_reset\_email.html

* **Sem funções**: Template HTML usado para o email de redefinição de senha.

---
