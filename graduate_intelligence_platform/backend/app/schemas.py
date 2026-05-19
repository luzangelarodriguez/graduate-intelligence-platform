from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Page(BaseModel):
    items: list[dict[str, Any]]
    count: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    db_name: str


class DashboardKpisResponse(BaseModel):
    kpis: dict[str, Any]
    source: str


class AlumniRegistrationIn(BaseModel):
    nombre_completo: str = Field(min_length=2)
    email: str = Field(min_length=3)
    especializacion_id: int
    anio_graduacion: str = ""
    cargo_actual: str = ""
    area_actual: str = ""
    nivel_experiencia: str = ""
    anios_experiencia: str = ""
    skills_actuales: str = ""
    herramientas_dia_dia: str = ""
    roles_interes: str = ""
    areas_interes: str = ""
    objetivo_laboral: str = ""
    disponibilidad: str = ""


class AlumniRegistrationOut(BaseModel):
    id: int
    status: str
    message: str


class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str
    roles: list[str]
    active: bool


class AuthRegisterIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    role: str = "egresado"


class AuthLoginIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class RefreshTokenIn(BaseModel):
    refresh_token: str = Field(min_length=16)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class LogoutIn(BaseModel):
    refresh_token: str | None = None
