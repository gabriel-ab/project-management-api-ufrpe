import os
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4
import datetime as dt

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, create_model
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from sqlalchemy.exc import NoResultFound


def patch(model: type[SQLModel]) -> type[SQLModel]:
    fields = model.model_fields.copy()
    for f in fields.values():
        f.required = False
        f.default = None

    return create_model(f"{model.__name__}Optional", **{n: (Optional[f.annotation], f) for n, f in fields.items()})


class Status(StrEnum):
    open = "OPEN"
    in_progress = "IN_PROGRESS"
    closed = "CLOSED"


class TeamEnum(StrEnum):
    requirements = "REQ"
    design = "DSN"
    development = "DEV"
    testing = "TEST"


class DatabaseMixin:
    created_at: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_at: dt.datetime = Field(
        default_factory=dt.datetime.now,
        sa_column_kwargs={"onupdate": dt.datetime.now},
    )

class ProjectBase(SQLModel):
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)


class TaskBase(SQLModel):
    team_id: UUID = Field(foreign_key="team.team_id")
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    status: Status = Field(...)


class ProjectCreate(ProjectBase):
    pass


class TaskCreate(TaskBase):
    dependencies: list[UUID] = Field(description="List of task IDs that this task depends on", default_factory=list)


class ProjectPatch(patch(ProjectCreate)):
    pass


class TaskPatch(patch(TaskCreate)):
    pass


class Team(ProjectBase, DatabaseMixin, table=True):
    team_id: UUID = Field(default_factory=uuid4, primary_key=True, description="Team ID")
    tasks: list["Task"] = Relationship(back_populates="team")


class Dependency(SQLModel, table=True):
    blocks: UUID = Field(..., foreign_key="task.task_id", primary_key=True)
    blocked: UUID = Field(..., foreign_key="task.task_id", primary_key=True)


class Task(TaskBase, DatabaseMixin, table=True):
    task_id: UUID = Field(default_factory=uuid4, primary_key=True, description="Task ID")
    team: Optional["Team"] = Relationship(back_populates="tasks")
    blocks: list["Task"] = Relationship(
        back_populates="blocked",
        link_model=Dependency,
        sa_relationship_kwargs=dict(
            foreign_keys=[Dependency.blocks,Dependency.blocked],
            primaryjoin="Task.task_id==Dependency.blocks",
            secondaryjoin="Task.task_id==Dependency.blocked",
        )
    )
    blocked: list["Task"] = Relationship(
        back_populates="blocks",
        link_model=Dependency,
        sa_relationship_kwargs=dict(
            foreign_keys=[Dependency.blocked, Dependency.blocks],
            primaryjoin="Task.task_id == Dependency.blocked",
            secondaryjoin="Task.task_id == Dependency.blocks"
        )
    )


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
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


def would_create_cycle(session: Session, source_id: UUID, target_id: UUID) -> bool:
    """
    Verifica se adicionar uma dependência source_id -> target_id criaria um ciclo.
    """
    visited = set()

    def dfs(task_id: UUID):
        if task_id == source_id:
            return True
        visited.add(task_id)

        blocked_tasks = session.exec(select(Dependency.blocked).where(Dependency.blocks == task_id)).all()

        for next_id in blocked_tasks:
            if next_id not in visited and dfs(next_id):
                return True

        return False

    return dfs(target_id)


@app.post("/team", response_model=Team, status_code=status.HTTP_201_CREATED)
def create_team(team: ProjectCreate, session: Session = Depends(get_session)):
    "Cria projeto do Usuário"
    team = Team(**team.model_dump())
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@app.get("/team", response_model=list[Team])
def read_teams(session: Session = Depends(get_session)):
    "Obtém projetos do Usuário"
    team = session.exec(select(Team)).all()
    return team


@app.patch("/team/{team_id}", response_model=Team)
def update_team(team_id: UUID, payment_update: ProjectPatch, session: Session = Depends(get_session)):
    "Atualiza projeto do Usuário"
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    try:
        for key, value in payment_update.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(team, key, value)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@app.delete("/team/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(team_id: UUID, session: Session = Depends(get_session)):
    "Apaga projeto do Usuário"
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()


@app.post("/task", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, session: Session = Depends(get_session)):
    "Cria tarefa tarefas do Usuário no Projeto `team`"
    data = Task(**task.model_dump(exclude={"dependencies"}))
    try:
        deps = [session.get_one(Task, dep) for dep in task.dependencies]
        data.blocked = deps
    except NoResultFound:
        raise HTTPException(status_code=404, detail="One or more dependencies not found")
    session.add(data)
    session.commit()
    session.refresh(data)
    return data


@app.get("/task", response_model=list[Task])
def read_tasks(team: UUID, session: Session = Depends(get_session)):
    "Obtém tarefas do Usuário no Projeto `team`"
    tasks = session.exec(select(Task).where(Task.team_id == team)).all()
    return tasks


@app.patch("/task/{task_id}", response_model=Task)
def update_task(task_id: UUID, task_update: TaskPatch, session: Session = Depends(get_session)):
    "Atualiza tarefa do Usuário"
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        for key, value in task_update.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(task, key, value)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.delete("/task/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: UUID, session: Session = Depends(get_session)):
    "Apaga tarefa do Usuário"
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()


@app.post("/task/{task_id}/depends/{target}", status_code=status.HTTP_201_CREATED)
def block_task(task_id: UUID, target: UUID, session: Session = Depends(get_session)):
    "Adiciona a tarefa `uuid` como pre requisito para a tarefa `target_id`"

    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_id == target:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself.")

    if would_create_cycle(session, task_id, target):
        raise HTTPException(status_code=400, detail="This dependency would create a cycle.")

    dependency = Dependency(blocks=target, blocked=task_id)
    session.add(dependency)
    session.commit()


@app.get("/task/{task_id}/blocks", response_model=list[Task])
def list_tasks_which_are_blocked_by_this_task(task_id: UUID, session: Session = Depends(get_session)):
    "Lista as tarefas que só serão feitas após esta"
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.blocks


@app.get("/task/{task_id}/depends", response_model=list[Task])
def list_tasks_which_this_task_depends_on(task_id: UUID, session: Session = Depends(get_session)):
    "Lista as tarefas que devem ser feitas antes desta"
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.blocked

