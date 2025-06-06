# TDAI 2025/Project/run_backend.py
import sys
import os
import uvicorn
from Backend.core.config import logger

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(project_root, "Backend")

    # Adiciona a pasta Backend ao sys.path para ajudar com os imports internos
    # que podem estar usando "app." (precisaremos verificar isso depois)
    # Por agora, o mais importante é o Uvicorn encontrar 'main:app'
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # Muda o diretório de trabalho atual para a pasta Backend
    try:
        os.chdir(backend_dir)
    except FileNotFoundError:
        logger.error("ERRO: O diretório Backend não foi encontrado em %s", backend_dir)
        sys.exit(1)

    logger.debug("--- sys.path atual ---")
    for p in sys.path:
        logger.debug(p)
    logger.debug("----------------------")
    logger.debug("Diretório de Trabalho Atual (CWD): %s", os.getcwd())
    logger.info("Tentando iniciar Uvicorn com 'main:app' a partir da pasta Backend...")

    try:
        uvicorn.run(
            "main:app",  # Alvo: arquivo main.py, objeto app dentro dele
            host="127.0.0.1",
            port=8000,
            reload=True,
            workers=1
        )
    except ImportError as e:
        logger.error("Erro de Importação ao tentar carregar a aplicação Uvicorn: %s", e)
        logger.error("Verifique se o arquivo 'main.py' existe em 'Backend/' e contém 'app = FastAPI()'.")
        logger.error("Verifique também os imports dentro de 'main.py'.")
    except Exception as e:
        logger.error("Ocorreu um erro inesperado ao tentar iniciar o Uvicorn: %s", e)
