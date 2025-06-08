# TDAI 2025/Project/run_backend.py
import sys
import os
import uvicorn
from Backend.core.config import logger

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(project_root, "Backend")

    # Adiciona o diretório raiz do projeto ao sys.path para que o pacote
    # "Backend" seja importável usando a sintaxe de pacote completa
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Alguns módulos dentro de "Backend" usam imports sem o prefixo do pacote
    # (por exemplo, ``from core.logging_config import get_logger``). Esses
    # imports funcionam apenas se o diretório ``Backend`` também estiver
    # presente em ``sys.path``. Ao incluir explicitamente ``backend_dir``,
    # garantimos que esses módulos possam ser resolvidos corretamente, mesmo
    # quando ``run_backend.py`` é executado a partir do diretório raiz do
    # projeto.
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # Não alteramos o diretório de trabalho para evitar que módulos dentro do
    # pacote sejam carregados como scripts de nível superior. Isso garante que
    # imports relativos (como os utilizados em crud.py) funcionem corretamente.

    logger.debug("--- sys.path atual ---")
    for p in sys.path:
        logger.debug(p)
    logger.debug("----------------------")
    logger.debug("Diretório de Trabalho Atual (CWD): %s", os.getcwd())
    logger.info("Tentando iniciar Uvicorn com 'Backend.main:app' ...")

    try:
        uvicorn.run(
            "Backend.main:app",  # Alvo: pacote Backend, módulo main.py, objeto app
            host="127.0.0.1",
            port=8000,
            reload=True,
            workers=1,
        )
    except ImportError as e:
        logger.error("Erro de Importação ao tentar carregar a aplicação Uvicorn: %s", e)
        logger.error("Verifique se o arquivo 'main.py' existe em 'Backend/' e contém 'app = FastAPI()'.")
        logger.error("Verifique também os imports dentro de 'main.py'.")
    except Exception as e:
        logger.error("Ocorreu um erro inesperado ao tentar iniciar o Uvicorn: %s", e)
