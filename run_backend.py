# CatalogAI 2025/Project/run_backend.py
import sys
import os
import argparse
import uvicorn
from Backend.core.config import logger

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(project_root, "Backend")

    # Assegura que o pacote ``Backend`` seja importável acrescentando o
    # diretório raiz do projeto ao ``sys.path``. Ao utilizar importações com o
    # prefixo ``Backend`` (por exemplo, ``from Backend.core.config import
    # settings``) não é necessário incluir ``backend_dir`` no ``sys.path``.
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Não alteramos o diretório de trabalho para evitar que módulos dentro do
    # pacote sejam carregados como scripts de nível superior. Isso garante que
    # imports relativos (como os utilizados em crud.py) funcionem corretamente.

    logger.debug("--- sys.path atual ---")
    for p in sys.path:
        logger.debug(p)
    logger.debug("----------------------")
    logger.debug("Diretório de Trabalho Atual (CWD): %s", os.getcwd())
    logger.info("Tentando iniciar Uvicorn com 'Backend.main:app' ...")

    parser = argparse.ArgumentParser(description="Run CatalogAI backend")

    def str_to_bool(value: str) -> bool:
        return str(value).lower() in {"1", "true", "yes", "y"}
    parser.add_argument(
        "--host",
        default=os.getenv("BACKEND_HOST", "127.0.0.1"),
        help="Host interface to bind",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("BACKEND_PORT", 8000)),
        help="Port to bind",
    )
    parser.add_argument(
        "--reload",
        type=str_to_bool,
        default=str_to_bool(os.getenv("BACKEND_RELOAD", "True")),
        help="Enable auto-reload",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("BACKEND_WORKERS", 1)),
        help="Number of worker processes",
    )

    args = parser.parse_args()

    try:
        uvicorn.run(
            "Backend.main:app",  # Alvo: pacote Backend, módulo main.py, objeto app
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
        )
    except ImportError as e:
        logger.error("Erro de Importação ao tentar carregar a aplicação Uvicorn: %s", e)
        logger.error("Verifique se o arquivo 'main.py' existe em 'Backend/' e contém 'app = FastAPI()'.")
        logger.error("Verifique também os imports dentro de 'main.py'.")
    except Exception as e:
        logger.error("Ocorreu um erro inesperado ao tentar iniciar o Uvicorn: %s", e)
