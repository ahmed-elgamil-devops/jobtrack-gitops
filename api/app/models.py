from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Status(str, Enum):
    applied = "Applied"
    interview = "Interview"
    offer = "Offer"
    rejected = "Rejected"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(60), default="LinkedIn")
    status: Mapped[str] = mapped_column(String(20), default=Status.applied.value)
    applied_on: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JobCreate(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=120)
    source: str = Field(default="LinkedIn", max_length=60)
    status: Status = Status.applied
    applied_on: date | None = None


class JobUpdate(BaseModel):
    status: Status


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    title: str
    source: str
    status: Status
    applied_on: date


class Stats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    response_rate: float
    interview_rate: float
