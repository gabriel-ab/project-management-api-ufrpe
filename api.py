import os
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4
import datetime as dt

from fastapi import Depends, FastAPI, HTTPException, APIRouter, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, create_model
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select


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


class DatabaseMixin:
    created_at: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_at: dt.datetime = Field(
        default_factory=dt.datetime.now,
        sa_column_kwargs={"onupdate": dt.datetime.now},
    )


class UserMixin(SQLModel):
    user_id: UUID = Field(index=True, description="UUID of the user_id")


class ProjectBase(SQLModel):
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)


class TaskBase(SQLModel):
    project_id: UUID = Field(foreign_key="project.project_id")
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    status: Status = Field(...)


class ProjectCreate(ProjectBase):
    pass


class TaskCreate(TaskBase):
    pass


class ProjectPatch(patch(ProjectCreate)):
    pass


class TaskPatch(patch(TaskCreate)):
    pass


class Project(ProjectCreate, DatabaseMixin, UserMixin, table=True):
    project_id: UUID = Field(default_factory=uuid4, primary_key=True, description="Project ID")
    tasks: list["Task"] = Relationship(back_populates="project")


class Dependency(SQLModel, table=True):
    blocks: UUID = Field(..., foreign_key="task.task_id", primary_key=True)
    blocked: UUID = Field(..., foreign_key="task.task_id", primary_key=True)


class Task(TaskCreate, DatabaseMixin, UserMixin, table=True):
    task_id: UUID = Field(default_factory=uuid4, primary_key=True, description="Task ID")
    project: Optional["Project"] = Relationship(back_populates="tasks")
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
    with Session(engine) as s:
        user_id = UUID('3fa85f64-5717-4562-b3fc-2c963f66afa6')
        p = Project(name='Projeto de Teste', description='Descrição de teste', user_id=user_id)
        a = Task(name='Fazer A', description='Descrição A', status=Status.open, user_id=user_id)
        b = Task(name='Fazer B', description='Descrição B', status=Status.open, user_id=user_id)
        c = Task(name='Fazer C', description='Descrição C', status=Status.open, blocked=[a], user_id=user_id)
        p.tasks.extend([a,b,c])
        s.add(p)
        s.commit()

    yield


app = FastAPI(
    title="Project Management API",
    description="API for managing projects and tasks",
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

router = APIRouter(prefix='/{user_id}')

@router.post("/project", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(user_id: UUID, project: ProjectCreate, session: Session = Depends(get_session)):
    "Cria projeto do Usuário"
    project = Project(user_id=user_id, **project.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/project", response_model=list[Project])
def read_projects(user_id: UUID, session: Session = Depends(get_session)):
    "Obtém projetos do Usuário"
    project = session.exec(select(Project).where(Project.user_id == user_id)).all()
    return project


@router.patch("/project/{project_id}", response_model=Project)
def update_project(user_id: UUID, project_id: UUID, payment_update: ProjectPatch, session: Session = Depends(get_session)):
    "Atualiza projeto do Usuário"
    project = session.get(Project, project_id)
    if not project or project.user_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        for key, value in payment_update.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(project, key, value)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/project/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(user_id: UUID, project_id: UUID, session: Session = Depends(get_session)):
    "Apaga projeto do Usuário"
    project = session.get(Project, project_id)
    if not project or project.user_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    session.delete(project)
    session.commit()


@router.post("/task", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(user_id: UUID, task: TaskCreate, session: Session = Depends(get_session)):
    "Cria tarefa tarefas do Usuário no Projeto `project`"
    task = Task(user_id=user_id, **task.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/task", response_model=list[Task])
def read_tasks(user_id: UUID, project: UUID, session: Session = Depends(get_session)):
    "Obtém tarefas do Usuário no Projeto `project`"
    tasks = session.exec(select(Task).where(Task.user_id == user_id, Task.project_id == project)).all()
    return tasks


@router.patch("/task/{task_id}", response_model=Task)
def update_task(user_id: UUID, task_id: UUID, task_update: TaskPatch, session: Session = Depends(get_session)):
    "Atualiza tarefa do Usuário"
    task = session.get(Task, task_id)
    if not task or task.user_id != user_id:
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


@router.delete("/task/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(user_id: UUID, task_id: UUID, session: Session = Depends(get_session)):
    "Apaga tarefa do Usuário"
    task = session.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()


@router.post("/task/{task_id}/blocks")
def block_task(user_id: UUID, task_id: UUID, target: UUID, session: Session = Depends(get_session)):
    "Adiciona a tarefa `uuid` como pre requisito para a tarefa `target_id`"

    task = session.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_id == target:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself.")

    if would_create_cycle(session, task_id, target):
        raise HTTPException(status_code=400, detail="This dependency would create a cycle.")

    dependency = Dependency(blocks=task_id, blocked=target)
    session.add(dependency)
    session.commit()


@router.get("/task/{task_id}/blocks", response_model=list[Task])
def list_tasks_which_are_blocked_by_this_task(user_id: UUID, task_id: UUID, session: Session = Depends(get_session)):
    "Lista as tarefas que só serão feitas após esta"
    task = session.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.blocks


@router.get("/task/{task_id}/blocked", response_model=list[Task])
def list_tasks_which_this_task_depends_on(user_id: UUID, task_id: UUID, session: Session = Depends(get_session)):
    "Lista as tarefas que devem ser feitas antes desta"
    task = session.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.blocked


app.include_router(router)