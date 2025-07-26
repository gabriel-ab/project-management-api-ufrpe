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
            "status": "OPEN",
        },
        {
            "name": "Requisitos de cadastro de clientes",
            "description": "Definir dados obrigatórios para clientes",
            "team": "REQ",
            "case_id": case_ids[1],
            "status": "OPEN",
        },
        {
            "name": "Requisitos de carrinho de compras",
            "description": "Detalhar regras do carrinho",
            "team": "REQ",
            "case_id": case_ids[1],
            "status": "OPEN",
        },
        {
            "name": "Requisitos de promoções",
            "description": "Especificar regras de descontos e cupons",
            "team": "REQ",
            "case_id": case_ids[0],
            "status": "OPEN",
        },
        # DES
        {
            "name": "Wireframe da página de produto",
            "description": "Desenhar layout para exibição de produtos",
            "team": "DES",
            "case_id": case_ids[0],
            "status": "OPEN",
            "dependencies": ["REQ-1", "REQ-4"],
        },
        {
            "name": "Protótipo do checkout",
            "description": "Criar protótipo navegável do fluxo de compra",
            "team": "DES",
            "case_id": case_ids[1],
            "status": "OPEN",
            "dependencies": ["REQ-2", "REQ-3"],
        },
        {
            "name": "Design do painel administrativo",
            "description": "Interface para gestão de produtos e pedidos",
            "team": "DES",
            "case_id": case_ids[0],
            "status": "OPEN",
            "dependencies": ["REQ-1"],
        },
        {
            "name": "Identidade visual do e-commerce",
            "description": "Definir paleta de cores e tipografia",
            "team": "DES",
            "case_id": case_ids[0],
            "status": "OPEN",
            "dependencies": ["REQ-1", "DES-1"],
        },
        # DEV
        {
            "name": "Implementar cadastro de produtos",
            "description": "CRUD de produtos com imagens",
            "team": "DEV",
            "case_id": case_ids[0],
            "status": "OPEN",
            "dependencies": ["DES-1"],
        },
        {
            "name": "API de pedidos",
            "description": "Endpoints para criação e consulta de pedidos",
            "team": "DEV",
            "case_id": case_ids[1],
            "status": "OPEN",
            "dependencies": ["DES-1", "DES-2"],
        },
        {
            "name": "Integração com gateway de pagamento",
            "description": "Processar pagamentos online",
            "team": "DEV",
            "case_id": case_ids[1],
            "status": "OPEN",
            "dependencies": ["REQ-3", "DES-3"],
        },
        {
            "name": "Cadastro de usuários",
            "description": "Permitir registro e autenticação de clientes",
            "team": "DEV",
            "case_id": case_ids[1],
            "status": "OPEN",
            "dependencies": ["REQ-2", "DES-3"],
        },
        # TES
        {
            "name": "Testes de unidade do backend",
            "description": "Cobrir regras de negócio com testes automatizados",
            "team": "TES",
            "case_id": case_ids[0],
            "status": "OPEN",
            "dependencies": ["DEV-2", "DEV-4"],
        },
        {
            "name": "Testes de integração do checkout",
            "description": "Validar fluxo completo de compra",
            "team": "TES",
            "case_id": case_ids[1],
            "status": "OPEN",
            "dependencies": ["DEV-3"],
        },
        {
            "name": "Testes de usabilidade",
            "description": "Avaliar experiência do usuário no site",
            "team": "TES",
            "case_id": case_ids[0],
            "status": "OPEN",
        },
        {
            "name": "Testes de performance",
            "description": "Medir tempo de resposta do sistema",
            "team": "TES",
            "case_id": case_ids[1],
            "status": "OPEN",
        },
    ]
    task_ids = []
    for t in tasks:
        resp = client.post("/task", json=t)
        resp.raise_for_status()
        task_ids.append(resp.json()["task_id"])

    print("Tasks created:", task_ids)

    resp = client.post("/task/TES-4/depends/DEV-4")
    resp.raise_for_status()
