from contextlib import contextmanager
from uuid import UUID
import datetime as dt
import os
from enum import StrEnum
from typing import Optional

from pydantic import computed_field, create_model
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
engine = create_engine(DATABASE_URL, echo=False)


def patch(cls: type[SQLModel]) -> type[SQLModel]:
    for f in cls.model_fields.values():
        f.required = False
        f.default = None
    return cls


def get_session():
    with Session(engine) as session:
        yield session


class StatusEnum(StrEnum):
    open = "OPEN"
    in_progress = "IN_PROGRESS"
    closed = "CLOSED"


class TeamEnum(StrEnum):
    requirements = "REQ"
    design = "DES"
    development = "DEV"
    testing = "TES"


class DatabaseMixin:
    created_at: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_at: dt.datetime = Field(
        default_factory=dt.datetime.now,
        sa_column_kwargs={"onupdate": dt.datetime.now},
    )


class CaseBase(SQLModel):
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)


class Case(CaseBase, DatabaseMixin, table=True):
    id: int = Field(primary_key=True, alias="case_id", description="Case ID")
    tasks: list["Task"] = Relationship(back_populates="case", cascade_delete=True)


class CaseCreate(CaseBase):
    pass


@patch
class CasePatch(CaseCreate):
    pass


class TeamTaskCounter(SQLModel, table=True):
    team_id: TeamEnum = Field(primary_key=True)
    last_id: int = 0


class Dependency(SQLModel, table=True):
    blocks: int = Field(..., foreign_key="task.id", primary_key=True)
    blocked: int = Field(..., foreign_key="task.id", primary_key=True)


class TaskBase(SQLModel):
    case_id: int = Field(foreign_key="case.id", description="ID of the use case this task belongs to")
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    status: StatusEnum = Field(...)
    team: TeamEnum = Field(default=TeamEnum.development, description="Team responsible for the task")


class Task(TaskBase, DatabaseMixin, table=True):
    id: int = Field(primary_key=True, alias="task_id", description="Task ID")
    nu: int = Field(description="Task number in the team")

    @computed_field
    @property
    def code(self) -> str:
        return f"{self.team}-{self.nu}"

    case: Case = Relationship(back_populates="tasks")
    depends: list["Task"] = Relationship(
        link_model=Dependency,
        sa_relationship_kwargs=dict(
            foreign_keys=[Dependency.blocked, Dependency.blocks],
            primaryjoin="Task.id == Dependency.blocked",
            secondaryjoin="Task.id == Dependency.blocks",
        ),
    )


class TaskCreate(TaskBase):
    dependencies: list[str] = Field(description="List of task IDs that this task depends on", default_factory=list)


@patch
class TaskPatch(TaskCreate):
    pass
