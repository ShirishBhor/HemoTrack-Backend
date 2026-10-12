from app.db.base import Base

# Import all models so Alembic and create_all() can discover them.
from app.models import (  # noqa: F401, E402
    Doctor,
    Gender,
    Patient,
    PatientType,
    TestCase,
    TestParameter,
    User,
    UserRole,
)

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Doctor",
    "Patient",
    "PatientType",
    "Gender",
    "TestCase",
    "TestParameter",
]
