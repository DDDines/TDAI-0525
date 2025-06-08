# Backend/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# --- INÍCIO DAS MODIFICAÇÕES PARA O SEU PROJETO ---
import os
import sys

# Obtém o caminho para o diretório atual do env.py (Backend/alembic/)
current_alembic_env_dir = os.path.dirname(os.path.abspath(__file__))
# Obtém o caminho para o diretório Backend (um nível acima de alembic/)
backend_root_dir = os.path.join(current_alembic_env_dir, '..')
# Obtém o caminho para a raiz do projeto (um nível acima de Backend/)
project_root_dir = os.path.join(backend_root_dir, '..')

# Adiciona o diretório 'Backend' ao sys.path
# Isso permite importar 'database' e 'models' diretamente quando executado de 'Backend'.
if backend_root_dir not in sys.path:
    sys.path.insert(0, backend_root_dir)
    print(f"INFO: '{backend_root_dir}' adicionado ao sys.path.")

# Tenta importar Base e models.
# Se a execução é a partir do diretório Backend, esses imports devem funcionar.
try:
    from Backend.database import Base  # Importa a Base definida em Backend/database.py
    import models              # Importa todos os modelos definidos em Backend/models.py
    target_metadata = Base.metadata
    print("INFO: models.Base e models importados com sucesso para Alembic.")
except ImportError as e:
    # Se o import direto falhou, é possível que 'Backend' não esteja sendo tratado como um pacote raiz
    # Tenta adicionar a raiz do projeto ao sys.path e importar usando o prefixo do pacote.
    print(f"AVISO: Tentativa de importação direta falhou: {e}. Tentando importação absoluta via raiz do projeto.")
    if project_root_dir not in sys.path:
        sys.path.insert(0, project_root_dir)
        print(f"INFO: '{project_root_dir}' (raiz do projeto) adicionado ao sys.path para imports de pacote.")
    try:
        from Backend.database import Base  # Importação absoluta: do pacote Backend
        import Backend.models as models    # Importação absoluta: do pacote Backend
        target_metadata = Base.metadata
        print("INFO: models.Base e models importados com sucesso usando caminho absoluto para Alembic.")
    except ImportError as inner_e:
        print(f"ERRO: Falha crítica ao importar Base ou models para Alembic mesmo com sys.path ajustado: {inner_e}")
        print("Verifique se 'database.py' e 'models.py' estão no diretório 'Backend' e se a estrutura de pacotes está correta.")
        target_metadata = None # Fallback, mas causará problemas de autogenerate


# Importa as configurações do seu projeto para obter a URL do banco de dados (se necessário)
try:
    from Backend.core.config import settings as app_settings
    # Usamos a URL de settings para garantir consistência.
    # alembic.ini também pode ter 'sqlalchemy.url', mas a de settings é preferível.
    SQLALCHEMY_DATABASE_URL = str(app_settings.DATABASE_URL)
    print("INFO: app_settings.DATABASE_URL carregada com sucesso.")
except ImportError as e:
    print(f"ERRO: Falha ao importar settings do core: {e}")
    SQLALCHEMY_DATABASE_URL = None # Deixa Alembic usar a URL do alembic.ini
# --- FIM DAS MODIFICAÇÕES PARA O SEU PROJETO ---


# Este é o objeto Alembic Config, que fornece
# acesso aos valores dentro do arquivo .ini em uso.
config = context.config

# Interpreta o arquivo de configuração para o logging do Python.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata já definido acima

# outros valores do config, definidos pelas necessidades do env.py,
# podem ser adquiridos:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Executa migrações no modo 'offline'.
    Isso configura o contexto apenas com uma URL.
    """
    url = SQLALCHEMY_DATABASE_URL if SQLALCHEMY_DATABASE_URL else config.get_main_option("sqlalchemy.url")

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
    Neste cenário, precisamos criar um Engine e associar uma conexão com o contexto.
    """
    connectable = None
    if SQLALCHEMY_DATABASE_URL:
        # Se a URL foi carregada de settings, use-a para criar o engine
        connectable = engine_from_config(
            {"sqlalchemy.url": SQLALCHEMY_DATABASE_URL},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    else:
        # Caso contrário, use a URL do alembic.ini
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
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
