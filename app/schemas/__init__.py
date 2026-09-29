from app.schemas.doctor import DoctorCreate, DoctorRead, DoctorUpdate
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.schemas.user import LoginRequest, Token, UserCreate, UserRead, UserUpdate

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "LoginRequest",
    "Token",
    "DoctorCreate",
    "DoctorRead",
    "DoctorUpdate",
    "PatientCreate",
    "PatientRead",
    "PatientUpdate",
]
