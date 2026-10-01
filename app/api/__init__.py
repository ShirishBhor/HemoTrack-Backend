from fastapi import APIRouter

from app.api import auth, doctors, patients 

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(doctors.router)
api_router.include_router(patients.router)
