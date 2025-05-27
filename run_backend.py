# TDAI 2025/Project/run_backend.py
import sys
import os
import uvicorn

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
        print(f"ERRO: O diretório Backend não foi encontrado em {backend_dir}")
        sys.exit(1)

    print("--- sys.path atual ---")
    for p in sys.path:
        print(p)
    print("----------------------")
    print(f"Diretório de Trabalho Atual (CWD): {os.getcwd()}") # Deve ser .../Project/Backend
    print("Tentando iniciar Uvicorn com 'main:app' a partir da pasta Backend...")

    try:
        uvicorn.run(
            "main:app",  # Alvo: arquivo main.py, objeto app dentro dele
            host="127.0.0.1",
            port=8000,
            reload=True,
            workers=1
        )
    except ImportError as e:
        print(f"\n!!!!!! Erro de Importação ao tentar carregar a aplicação Uvicorn !!!!!!!")
        print(f"Detalhe do Erro: {e}")
        print("Verifique se o arquivo 'main.py' existe em 'Backend/' e contém 'app = FastAPI()'.")
        print("Verifique também os imports dentro de 'main.py'.")
    except Exception as e:
        print(f"\n!!!!!! Ocorreu um erro inesperado ao tentar iniciar o Uvicorn !!!!!!!")
        print(f"Detalhe do Erro: {e}")