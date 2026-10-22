from fastapi import APIRouter
from app.api import (
    accounts,
    auth,
    bills,
    doctors,
    expenses,
    patients,
    payments,
    refunds,
    test_cases,
    test_parameters,
    users,
    test_categories,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(doctors.router)
api_router.include_router(patients.router)
api_router.include_router(test_categories.router)
api_router.include_router(test_cases.router)
api_router.include_router(test_parameters.router)
api_router.include_router(bills.router)
api_router.include_router(payments.router)
api_router.include_router(expenses.router)
api_router.include_router(refunds.router)
api_router.include_router(accounts.router)
api_router.include_router(users.router)


