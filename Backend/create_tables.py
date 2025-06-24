# Salve este arquivo como Backend/create_tables.py
import os
import sys
from sqlalchemy import create_engine

print("Iniciando script de criação de tabelas (versão síncrona)...")

# --- Adiciona a pasta raiz do projeto ao Python Path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f"Raiz do projeto ({project_root}) adicionada ao path.")

try:
    from Backend.core.config import settings
    from Backend.database import Base
    import Backend.models  # Importa para registrar os modelos no Base
    print("Módulos importados com sucesso.")
except Exception as e:
    print(f"ERRO ao importar módulos: {e}")
    sys.exit(1)

def create_all_tables():
    print("Criando engine SÍNCRONO para a criação das tabelas...")
    try:
        # Pega a URL do banco do seu .env e a torna compatível com a engine síncrona
        db_url = str(settings.DATABASE_URL).replace('+asyncpg', '')
        sync_engine = create_engine(db_url)
        
        print("Conectando ao banco de dados...")
        # Conecta e cria todas as tabelas
        Base.metadata.create_all(sync_engine)
        
        print("\n>>> SUCESSO! Todas as tabelas foram criadas no banco de dados. <<<")
        print("Agora você pode iniciar a aplicação.")
    except Exception as e:
        print(f"\nERRO ao criar as tabelas: {e}")
        print("Verifique se as credenciais do banco no arquivo .env estão corretas e se o banco de dados 'tdai_db' existe.")

if __name__ == "__main__":
    create_all_tables()