## Backend - Project Management API

Este backend implementa uma API para gerenciamento de projetos e tarefas, utilizando FastAPI, SQLModel e SQLite.

### Funcionalidades principais
- CRUD de projetos e tarefas
- Relacionamento de dependências entre tarefas (bloqueios)
- Detecção automática de ciclos em dependências de tarefas
- Suporte a múltiplos usuários (por UUID)

### Como rodar
1. Instale as dependências:
   ```bash
   uv sync
   ```
2. Execute a API:
   ```bash
   fastapi run
   ```
2. Execute a API com dados Mockados:
   ```bash
   DATABASE_RESET=1 DATABASE_POPULATE=1 fastapi run
   ```
> Se preferir usar o docker: `docker compose up -d`

O `compose.yaml` usa dados mockados automáticamente

### Testes
Os testes automatizados estão no arquivo `test.py`.
Para rodar:
```bash
pytest test.py
```

---
Projeto desenvolvido para fins acadêmicos na UFRPE.
