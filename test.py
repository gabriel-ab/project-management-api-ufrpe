import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

USER_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def test_create_and_get_project():
    data = {"name": "Projeto Teste", "description": "Descrição do projeto"}
    response = client.post(f"/{USER_ID}/project", json=data)
    assert response.status_code == 201
    project = response.json()
    assert project["name"] == data["name"]
    assert project["description"] == data["description"]
    # Get projects
    response = client.get(f"/{USER_ID}/project")
    assert response.status_code == 200
    projects = response.json()
    assert any(p["name"] == data["name"] for p in projects)


def test_create_and_get_task():
    # Create project
    project_data = {"name": "Projeto Tarefa", "description": "Projeto para tarefa"}
    project_resp = client.post(f"/{USER_ID}/project", json=project_data)
    project_id = project_resp.json()["project_id"]
    # Create task
    task_data = {"project_id": project_id, "name": "Tarefa 1", "description": "Desc Tarefa", "status": "OPEN"}
    task_resp = client.post(f"/{USER_ID}/task", json=task_data)
    assert task_resp.status_code == 201
    task = task_resp.json()
    assert task["name"] == task_data["name"]
    # Get tasks
    resp = client.get(f"/{USER_ID}/task", params={"project": project_id})
    assert resp.status_code == 200
    tasks = resp.json()
    assert any(t["name"] == task_data["name"] for t in tasks)


def test_task_cycle_detection():
    # Cria projeto
    project_data = {"name": "Projeto Ciclo", "description": "Projeto para ciclo"}
    project_resp = client.post(f"/{USER_ID}/project", json=project_data)
    project_id = project_resp.json()["project_id"]
    # Cria duas tarefas
    task1_data = {"project_id": project_id, "name": "Task 1", "description": "Tarefa 1", "status": "OPEN"}
    task2_data = {"project_id": project_id, "name": "Task 2", "description": "Tarefa 2", "status": "OPEN"}
    task1_resp = client.post(f"/{USER_ID}/task", json=task1_data)
    task2_resp = client.post(f"/{USER_ID}/task", json=task2_data)
    task1_id = task1_resp.json()["task_id"]
    task2_id = task2_resp.json()["task_id"]
    # task1 bloqueia task2
    resp1 = client.post(f"/{USER_ID}/task/{task1_id}/blocks", params={"target": task2_id})
    assert resp1.status_code == 200
    # task2 bloqueia task1 (deve dar erro de ciclo)
    resp2 = client.post(f"/{USER_ID}/task/{task2_id}/blocks", params={"target": task1_id})
    assert resp2.status_code == 400
    assert "cycle" in resp2.json()["detail"].lower()


if __name__ == '__main__':
    pytest.main()