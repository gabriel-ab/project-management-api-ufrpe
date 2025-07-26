import os
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.exc import NoResultFound
from sqlmodel import Session, SQLModel, select

from .db import (
    CodeOrID,
    Case,
    CaseCreate,
    CasePatch,
    Dependency,
    Task,
    TaskCreate,
    TaskPatch,
    TaskWithDependencies,
    TeamEnum,
    engine,
    get_session,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("DATABASE_RESET", "false").lower() != "false":
        print("Resetting database...")
        SQLModel.metadata.drop_all(engine)

    SQLModel.metadata.create_all(engine)

    if os.getenv("DATABASE_POPULATE", "false").lower() != "false":
        from .mock import create_mock_data

        print("Populating database with mock data...")
        create_mock_data(app)

    yield


app = FastAPI(
    title="Team Management API",
    description="API for managing teams and tasks",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "UP"}


def get_task_by_code_or_id(session: Session, id_or_code: str):
    """
    Obtém uma tarefa com base em um identificador ou código.

    Se um inteiro for fornecido, retorna a tarefa com esse ID. (ex: 1)

    Se uma string de `code` for fornecido, retorna a tarefa com esse código. (ex: DEV-1)
    """
    if id_or_code.isdigit():
        task = session.get(Task, int(id_or_code))
    else:
        team, nu = id_or_code.split("-")
        task = session.exec(select(Task).where(Task.team == team, Task.nu == int(nu))).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {id_or_code} not found")
    return task


def would_create_cycle(session: Session, source_id: int, target_id: int) -> bool:
    """
    Verifica se adicionar uma dependência source_id -> target_id criaria um ciclo.
    """
    visited = set()

    def dfs(task_id: int):
        if task_id == source_id:
            return True
        visited.add(task_id)

        blocked_tasks = session.exec(select(Dependency.blocked).where(Dependency.blocks == task_id)).all()

        for next_id in blocked_tasks:
            if next_id not in visited and dfs(next_id):
                return True

        return False

    return dfs(target_id)


@app.post("/case", response_model=Case, status_code=status.HTTP_201_CREATED)
def create_case(case: CaseCreate, session: Session = Depends(get_session)):
    "Cria um caso de uso"
    data = Case(**case.model_dump())
    session.add(data)
    session.commit()
    session.refresh(data)
    return data


@app.get("/case", response_model=list[Case])
def read_cases(session: Session = Depends(get_session)):
    "Obtém casos de uso"
    return session.exec(select(Case)).all()


@app.patch("/case/{id}", response_model=Case)
def update_case(id: int, data_update: CasePatch, session: Session = Depends(get_session)):
    "Atualiza Caso de Uso"
    data = session.get(Case, id)
    if not data:
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        for key, value in data_update.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(data, key, value)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    session.add(data)
    session.commit()
    session.refresh(data)
    return data


@app.delete("/case/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(id: UUID, session: Session = Depends(get_session)):
    "Apaga Caso de Uso"
    data = session.get(Case, id)
    if not data:
        raise HTTPException(status_code=404, detail="Case not found")
    session.delete(data)
    session.commit()


@app.post("/task", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, session: Session = Depends(get_session)):
    "Cria tarefa"
    nu = 1 + (session.exec(select(func.max(Task.nu)).where(Task.team == task.team)).first() or 0)
    data = Task(nu=nu, **task.model_dump(exclude={"dependencies"}))
    if task.dependencies:
        try:
            data.dependencies = [get_task_by_code_or_id(session, dep) for dep in task.dependencies]
        except NoResultFound:
            raise HTTPException(status_code=404, detail="One or more dependencies not found")
    session.add(data)
    session.commit()
    session.refresh(data)
    return data


@app.get("/task", response_model=list[Task])
def read_tasks(team: TeamEnum = None, case_id: int = None, session: Session = Depends(get_session)):
    "Obtém tarefas"
    query = select(Task)
    if team is not None:
        query = query.where(Task.team == team)
    if case_id is not None:
        query = query.where(Task.case_id == case_id)
    return session.exec(query).all()

@app.get("/task-with-deps", response_model=list[TaskWithDependencies])
def read_tasks_with_dependencies(team: TeamEnum = None, case_id: int = None, session: Session = Depends(get_session)):
    "Obtém tarefas e suas dependências"
    query = select(Task)
    if team is not None:
        query = query.where(Task.team == team)
    if case_id is not None:
        query = query.where(Task.case_id == case_id)
    return session.exec(query).all()


@app.get("/task/{id}", response_model=Task)
def read_task(id: CodeOrID, session: Session = Depends(get_session)):
    "Obtém tarefa com base em um identificador ou código"
    return get_task_by_code_or_id(session, id)


@app.patch("/task/{id}", response_model=Task)
def update_task(id: CodeOrID, task_update: TaskPatch, session: Session = Depends(get_session)):
    "Atualiza tarefa do Usuário"
    task = get_task_by_code_or_id(session, id)
    try:
        for key, value in task_update.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(task, key, value)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.delete("/task/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: CodeOrID, session: Session = Depends(get_session)):
    "Apaga tarefa do Usuário"
    task = get_task_by_code_or_id(session, id)
    session.delete(task)
    session.commit()


@app.get("/task/{id}/depends", response_model=list[Task])
def list_tasks_which_this_task_depends_on(id: CodeOrID, session: Session = Depends(get_session)):
    "Lista as tarefas que devem ser feitas antes desta"
    task = get_task_by_code_or_id(session, id)
    return task.dependencies


@app.post("/task/{task_a}/depends/{task_b}", status_code=status.HTTP_201_CREATED)
def add_task_dependency(task_a: CodeOrID, task_b: CodeOrID, session: Session = Depends(get_session)):
    "Adiciona a tarefa `task_b` como pre requisito para a tarefa `task_a`"

    task = get_task_by_code_or_id(session, task_a)
    other = get_task_by_code_or_id(session, task_b)
    if task.id == other.id:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself.")

    if would_create_cycle(session, task.id, other.id):
        raise HTTPException(status_code=400, detail="This dependency would create a cycle.")

    dependency = Dependency(blocks=other.id, blocked=task.id)
    session.add(dependency)
    session.commit()


@app.delete("/task/{task_a}/depends/{task_b}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task_dependency(task_a: CodeOrID, task_b: CodeOrID, session: Session = Depends(get_session)):
    """
    Remove a dependência de `task_b` como pré-requisito para a tarefa `task_a`
    """
    task = get_task_by_code_or_id(session, task_a)
    other = get_task_by_code_or_id(session, task_b)

    dependency = session.get(Dependency, (task.id, other.id))
    if not dependency:
        raise HTTPException(status_code=404, detail="Dependency not found")

    session.delete(dependency)
    session.commit()
