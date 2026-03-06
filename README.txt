CatalogAI (TDAI-0525)

Este arquivo e um resumo rapido.
Para instrucoes completas e atualizadas, use:
- README.md (raiz de Project)
- docs/EXECUCAO_LOCAL.md
- Frontend/app/README.md

Passos minimos:
1) Copiar .env.example para .env e definir APP_MODE=oop
2) Backend: pip install -r requirements-backend.txt
3) Backend: alembic -c Backend/alembic.ini upgrade head
4) Backend: python run_backend.py
5) Frontend: cd Frontend/app && npm install && npm run dev

URLs:
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
