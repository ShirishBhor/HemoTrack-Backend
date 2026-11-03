from fastapi import APIRouter
from app.api import (
    accounts,
    agents,
    auth,
    bills,
    collection_centers,
    departments,
    doctors,
    expenses,
    lab_orders,
    patients,
    payments,
    refunds,
    test_cases,
    test_parameters,
    users,
    packages
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(doctors.router)
api_router.include_router(collection_centers.router)
api_router.include_router(agents.router)
api_router.include_router(patients.router)
api_router.include_router(departments.router)
api_router.include_router(packages.router)
api_router.include_router(test_cases.router)
api_router.include_router(test_parameters.router)
api_router.include_router(bills.router)
api_router.include_router(payments.router)
api_router.include_router(expenses.router)
api_router.include_router(refunds.router)
api_router.include_router(accounts.router)
api_router.include_router(lab_orders.router)
