from fastapi import FastAPI
from fastapi.testclient import TestClient


def create_mock_data(app: FastAPI):
    """
    Cria dados mockados usando as rotas da API (POST /case, /task, /task/{task_id}/depends/{other_task_id})
    """
    client = TestClient(app)
    cases = [
        {"name": "Cadastro de Produtos", "description": "Gerenciamento de produtos do e-commerce"},
        {"name": "Processamento de Pedidos", "description": "Fluxo de pedidos e pagamentos"},
    ]
    case_ids = []
    for c in cases:
        resp = client.post("/case", json=c)
        resp.raise_for_status()
        case_ids.append(resp.json()["case_id"])

    tasks = [
        # REQ
        {
            "name": "Levantamento de requisitos de catálogo",
            "description": "Mapear atributos necessários para produtos",
            "team": "REQ",
            "case_id": case_ids[0],
            "nu": 1,
            "status": "OPEN",
        },
        {
            "name": "Requisitos de cadastro de clientes",
            "description": "Definir dados obrigatórios para clientes",
            "team": "REQ",
            "case_id": case_ids[1],
            "nu": 2,
            "status": "OPEN",
        },
        {
            "name": "Requisitos de carrinho de compras",
            "description": "Detalhar regras do carrinho",
            "team": "REQ",
            "case_id": case_ids[1],
            "nu": 3,
            "status": "OPEN",
        },
        {
            "name": "Requisitos de promoções",
            "description": "Especificar regras de descontos e cupons",
            "team": "REQ",
            "case_id": case_ids[0],
            "nu": 4,
            "status": "OPEN",
        },
        # DES
        {
            "name": "Wireframe da página de produto",
            "description": "Desenhar layout para exibição de produtos",
            "team": "DES",
            "case_id": case_ids[0],
            "nu": 1,
            "status": "OPEN",
        },
        {
            "name": "Protótipo do checkout",
            "description": "Criar protótipo navegável do fluxo de compra",
            "team": "DES",
            "case_id": case_ids[1],
            "nu": 2,
            "status": "OPEN",
        },
        {
            "name": "Design do painel administrativo",
            "description": "Interface para gestão de produtos e pedidos",
            "team": "DES",
            "case_id": case_ids[0],
            "nu": 3,
            "status": "OPEN",
        },
        {
            "name": "Identidade visual do e-commerce",
            "description": "Definir paleta de cores e tipografia",
            "team": "DES",
            "case_id": case_ids[0],
            "nu": 4,
            "status": "OPEN",
        },
        # DEV
        {
            "name": "Implementar cadastro de produtos",
            "description": "CRUD de produtos com imagens",
            "team": "DEV",
            "case_id": case_ids[0],
            "nu": 1,
            "status": "OPEN",
        },
        {
            "name": "API de pedidos",
            "description": "Endpoints para criação e consulta de pedidos",
            "team": "DEV",
            "case_id": case_ids[1],
            "nu": 2,
            "status": "OPEN",
        },
        {
            "name": "Integração com gateway de pagamento",
            "description": "Processar pagamentos online",
            "team": "DEV",
            "case_id": case_ids[1],
            "nu": 3,
            "status": "OPEN",
        },
        {
            "name": "Cadastro de usuários",
            "description": "Permitir registro e autenticação de clientes",
            "team": "DEV",
            "case_id": case_ids[1],
            "nu": 4,
            "status": "OPEN",
        },
        # TES
        {
            "name": "Testes de unidade do backend",
            "description": "Cobrir regras de negócio com testes automatizados",
            "team": "TES",
            "case_id": case_ids[0],
            "nu": 1,
            "status": "OPEN",
        },
        {
            "name": "Testes de integração do checkout",
            "description": "Validar fluxo completo de compra",
            "team": "TES",
            "case_id": case_ids[1],
            "nu": 2,
            "status": "OPEN",
        },
        {
            "name": "Testes de usabilidade",
            "description": "Avaliar experiência do usuário no site",
            "team": "TES",
            "case_id": case_ids[0],
            "nu": 3,
            "status": "OPEN",
        },
        {
            "name": "Testes de performance",
            "description": "Medir tempo de resposta do sistema",
            "team": "TES",
            "case_id": case_ids[1],
            "nu": 4,
            "status": "OPEN",
        },
    ]
    task_ids = []
    for t in tasks:
        resp = client.post("/task", json=t)
        resp.raise_for_status()
        task_ids.append(resp.json()["task_id"])

    print("Tasks created:", task_ids)

    # Dependências (índices iguais aos da lista tasks)
    dependencies = [
        (4, 0),  # Wireframe depende de requisitos de catálogo
        (5, 2),  # Protótipo do checkout depende de requisitos de carrinho
        (8, 4),  # Implementar cadastro depende do wireframe
        (9, 5),  # API de pedidos depende do protótipo do checkout
        (10, 9),  # Integração pagamento depende da API de pedidos
        (12, 8),  # Testes backend depende do cadastro de produtos
        (13, 10),  # Testes integração depende da integração pagamento
        (14, 7),  # Testes usabilidade depende da identidade visual
        (1, 0),  # Requisitos de clientes depende de requisitos de catálogo
        (2, 1),  # Requisitos de carrinho depende de requisitos de clientes
        (6, 4),  # Design painel depende do wireframe
        (7, 6),  # Identidade visual depende do painel admin
        (11, 8),  # Cadastro usuários depende do cadastro de produtos
        (15, 12),  # Testes performance depende dos testes backend
    ]
    for depender_idx, dependee_idx in dependencies:
        depender_id = task_ids[depender_idx]
        dependee_id = task_ids[dependee_idx]
        resp = client.post(f"/task/{depender_id}/depends/{dependee_id}")
        resp.raise_for_status()
