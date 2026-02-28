import os
import sys
from typing import Optional

from sqlalchemy import create_engine

print("Iniciando script de criacao de tabelas (versao sincrona)...")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f"Raiz do projeto ({project_root}) adicionada ao path.")

try:
    from Backend.core.config import settings
    from Backend.database import Base
    import Backend.models  # noqa: F401

    print("Modulos importados com sucesso.")
except Exception as exc:
    print(f"ERRO ao importar modulos: {exc}")
    sys.exit(1)

class _CreateTablesWorkflow:
    def __init__(self, runtime: Optional["_CreateTablesRuntime"] = None) -> None:
        self._runtime = runtime or _CreateTablesRuntime()

    def create_all_tables(self):
        self._runtime.create_all_tables()


class _CreateTablesRuntime:
    def create_all_tables(self):
        print("Criando engine sincrono para criacao das tabelas...")
        try:
            db_url = str(settings.DATABASE_URL).replace("+asyncpg", "")
            sync_engine = create_engine(db_url)
            print("Conectando ao banco de dados...")
            Base.metadata.create_all(sync_engine)
            print("\n>>> SUCESSO! Todas as tabelas foram criadas no banco de dados. <<<")
            print("Agora voce pode iniciar a aplicacao.")
        except Exception as exc:
            print(f"\nERRO ao criar as tabelas: {exc}")
            print(
                "Verifique as credenciais do banco no .env e se o banco "
                "de dados configurado existe."
            )


_create_tables_workflow = _CreateTablesWorkflow()
CreateTablesWorkflow = _CreateTablesWorkflow


def get_create_tables_workflow() -> CreateTablesWorkflow:
    return _create_tables_workflow


def create_all_tables():
    _create_tables_workflow.create_all_tables()




if __name__ == "__main__":
    create_all_tables()

