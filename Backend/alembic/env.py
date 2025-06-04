# Backend/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# --- INÍCIO DAS MODIFICAÇÕES PARA O SEU PROJETO ---
import os
import sys
from dotenv import load_dotenv # Para carregar a URL do banco do .env

# Adiciona o diretório 'Backend' ao sys.path para que possamos importar 'database' e 'models'
# O arquivo env.py está em Backend/alembic/, então precisamos subir um nível para Backend/
# e então garantir que este diretório esteja no path para os imports.
# Na verdade, como o alembic é geralmente executado da pasta 'Backend',
# os módulos dentro de 'Backend' (como database, models, core) devem ser
# diretamente importáveis. Vamos simplificar o ajuste de path.

# Assume-se que o comando 'alembic' será executado da pasta 'Backend'.
# Se você executar da raiz do projeto, os imports abaixo precisarão ser ajustados (ex: from Backend.database import Base)

# Carrega variáveis de ambiente do arquivo .env que está na raiz do projeto
# (um nível acima de 'Backend', dois níveis acima de 'alembic')
# Ajuste o caminho para o .env conforme a sua estrutura
# Se o alembic.ini está em Backend/, e run_backend.py está na raiz,
# e o .env está na raiz do projeto:
#   PROJECT_ROOT/
#   ├── .env
#   ├── Backend/
#   │   ├── alembic.ini
#   │   └── alembic/
#   │       └── env.py
#   └── run_backend.py
# Então, de alembic/env.py, o .env está dois níveis acima.
# No entanto, é mais comum que a URL do banco para o Alembic seja lida
# diretamente do alembic.ini (que já fizemos) ou que o settings seja usado aqui.

# Opção 1: Usar as configurações do seu projeto FastAPI para obter a URL do banco
# Isso é geralmente mais robusto, pois centraliza a configuração.
try:
    # Adiciona o diretório 'Backend' ao path se necessário para importar 'core.config'
    # Se executando alembic da pasta 'Backend', isso pode não ser estritamente necessário
    # mas não faz mal garantir.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from core.config import settings as app_settings # Importa o objeto settings
    SQLALCHEMY_DATABASE_URL = str(app_settings.DATABASE_URL) # Converte para string
except ImportError as e:
    print(f"Erro ao importar settings para Alembic: {e}")
    print("Certifique-se de que o alembic está sendo executado do diretório Backend ou ajuste o sys.path.")
    # Fallback para ler diretamente do .env se a importação de settings falhar,
    # ou defina a URL manualmente se o alembic.ini já estiver configurado.
    # Se alembic.ini já tem sqlalchemy.url, esta parte é apenas para o target_metadata.
    # A URL no alembic.ini será usada por padrão pelo engine_from_config.
    # A principal razão para carregar settings aqui é para o target_metadata.
    # No entanto, a URL também pode ser configurada aqui programaticamente se necessário.
    # Para agora, vamos assumir que alembic.ini está correto para a URL.
    pass


# Importe a Base dos seus modelos SQLAlchemy e todos os seus modelos
# para que sejam registrados com Base.metadata
try:
    # Se 'database.py' e 'models.py' estão no mesmo nível que esta pasta 'alembic'
    # (ou seja, dentro de 'Backend/'), o import direto deve funcionar
    # se o comando 'alembic' for executado da pasta 'Backend'.
    from database import Base  # Onde seu `Base = declarative_base()` é definido
    import models            # Importa todos os modelos para registrar no Base.metadata
    target_metadata = Base.metadata
except ImportError as e:
    print(f"Erro ao importar Base ou models para Alembic: {e}")
    print("Verifique se 'database.py' e 'models.py' estão acessíveis no PYTHONPATH (geralmente na pasta Backend).")
    target_metadata = None
# --- FIM DAS MODIFICAÇÕES PARA O SEU PROJETO ---


# Este é o objeto Alembic Config, que fornece
# acesso aos valores dentro do arquivo .ini em uso.
config = context.config

# Interpreta o arquivo de configuração para o logging do Python.
# Esta linha basicamente configura os loggers.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Adicione aqui os metadados do seu modelo para suporte a 'autogenerate'
# target_metadata = None (Já definido acima)

# outros valores do config, definidos pelas necessidades do env.py,
# podem ser adquiridos:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Executa migrações no modo 'offline'.

    Isso configura o contexto apenas com uma URL
    e não um Engine, embora um Engine também seja
    aceitável aqui. Ao pular a criação do Engine,
    não precisamos nem mesmo que um DBAPI esteja disponível.

    As chamadas para context.execute() emitem a string dada para a
    saída do script.

    """
    # Se você configurou SQLALCHEMY_DATABASE_URL programaticamente acima, use-a.
    # Caso contrário, o Alembic usará a URL do alembic.ini.
    url = config.get_main_option("sqlalchemy.url") # Pega do alembic.ini
    # Se você carregou app_settings e quer usar a URL dali:
    # if 'SQLALCHEMY_DATABASE_URL' in locals() and SQLALCHEMY_DATABASE_URL:
    #     url = SQLALCHEMY_DATABASE_URL
    # else:
    #     url = config.get_main_option("sqlalchemy.url") # Fallback para alembic.ini

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrações no modo 'online'.

    Neste cenário, precisamos criar um Engine
    e associar uma conexão com o contexto.

    """
    # Usa a seção de configuração do alembic.ini que corresponde ao nome do engine (padrão: sqlalchemy)
    # ou, se você definiu SQLALCHEMY_DATABASE_URL via settings, pode criar o engine com ele.
    
    # Se você quer usar a URL das suas configurações do app FastAPI:
    # connectable_config = config.get_section(config.config_ini_section)
    # if 'SQLALCHEMY_DATABASE_URL' in locals() and SQLALCHEMY_DATABASE_URL:
    #     connectable_config['sqlalchemy.url'] = SQLALCHEMY_DATABASE_URL
    # connectable = engine_from_config(
    #     connectable_config, # Usa a seção do ini, possivelmente sobrescrevendo a url
    #     prefix="sqlalchemy.", # Alembic espera que as chaves do engine comecem com 'sqlalchemy.'
    #     poolclass=pool.NullPool,
    # )

    # Configuração padrão que lê do alembic.ini:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), # Adicionado {} como default
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()