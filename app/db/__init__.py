from app.db.base import Base

# Import models so Alembic and create_all see them.
from app.models import Doctor, Patient, User  # noqa: F401, E402

__all__ = ["Base", "User", "Doctor", "Patient"]
