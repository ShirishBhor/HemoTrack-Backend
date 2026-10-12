from fastapi import APIRouter
from app.api import auth, doctors, patients, users, test_cases, test_parameters

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(doctors.router)
api_router.include_router(patients.router)
api_router.include_router(test_cases.router)
api_router.include_router(test_parameters.router)