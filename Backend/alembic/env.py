import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Adiciona a pasta raiz do projeto ao Python Path ---
# Isso é CRUCIAL para que o Alembic encontre os módulos do seu projeto,
# como 'database', 'models', e 'core.config'.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configuração do Alembic ---
config = context.config

# Interpreta o arquivo de configuração para logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Configuração do Banco de Dados a partir do .env do projeto ---
# Importa as configurações da sua aplicação para pegar a URL do banco de dados
try:
    from Backend.core.config import settings as app_settings
    # Seta a URL do banco no config do Alembic dinamicamente
    config.set_main_option('sqlalchemy.url', str(app_settings.DATABASE_URL))
    print("URL do Banco de Dados carregada com sucesso para o Alembic.")
except ImportError as e:
    print(f"Erro Crítico: Não foi possível importar as configurações do projeto: {e}")
    sys.exit(1)

# --- Definição dos Metadados do Modelo para Autogenerate ---
# Importa a Base e todos os modelos para que o Alembic possa detectá-los
try:
    from Backend.database import Base
    import Backend.models  # Esta linha garante que os modelos sejam registrados
    print("Modelos do projeto (Base e Tabelas) importados com sucesso.")
except ImportError as e:
    print(f"Erro Crítico: Não foi possível importar os modelos do banco de dados: {e}")
    sys.exit(1)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
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