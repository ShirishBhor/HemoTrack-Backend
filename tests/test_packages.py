"""
Unit and integration tests for Package Master APIs and Service.
"""

import unittest
from decimal import Decimal

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import packages
from app.db import Base
from app.models.department import Department
from app.models.package import Package
from app.models.test_case import TestCase
from app.models.user import User, UserRole
from app.schemas.package import (
    PackageCreate,
    PackageRead,
    PackageUpdate,
    PackageWithTestsRead,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestPackageMasterModule(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.TestingSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()

        # Seed Users
        self.admin = User(
            email="admin_pkg@test.com",
            hashed_password="fakehashedpassword",
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.tech = User(
            email="tech_pkg@test.com",
            hashed_password="fakehashedpassword",
            full_name="Lab Tech",
            role=UserRole.LAB_TECHNICIAN,
            is_active=True,
        )
        self.db.add_all([self.admin, self.tech])
        self.db.commit()

        # Seed Department
        self.dept = Department(
            name="Biochemistry",
            code="BIO",
            is_active=True,
        )
        self.db.add(self.dept)
        self.db.commit()

        # Seed Tests
        self.test1 = TestCase(
            name="Complete Blood Count",
            code="CBC",
            price=Decimal("300.00"),
            department_id=self.dept.id,
            is_active=True,
        )
        self.test2 = TestCase(
            name="Lipid Profile",
            code="LIPID",
            price=Decimal("600.00"),
            department_id=self.dept.id,
            is_active=True,
        )
        self.test_inactive = TestCase(
            name="Deprecated Old Test",
            code="OLD_TEST",
            price=Decimal("150.00"),
            department_id=self.dept.id,
            is_active=False,
        )
        self.db.add_all([self.test1, self.test2, self.test_inactive])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_01_create_package_success(self):
        payload = PackageCreate(
            name="Executive Health Package",
            code="PKG-EXEC-01",
            description="Routine health checkup",
            price=Decimal("750.00"),
            tat="24 Hours",
            sample_requirements="Fasting Blood (EDTA + Serum)",
            fasting_required=True,
            department_id=self.dept.id,
            test_case_ids=[self.test1.id, self.test2.id],
        )

        pkg = packages.create_package(payload=payload, db=self.db, _=self.admin)
        self.assertIsNotNone(pkg.id)
        self.assertEqual(pkg.name, "Executive Health Package")
        self.assertEqual(pkg.code, "PKG-EXEC-01")
        self.assertEqual(pkg.price, Decimal("750.00"))
        self.assertTrue(pkg.fasting_required)
        self.assertEqual(pkg.test_count, 2)
        self.assertEqual(len(pkg.test_cases), 2)
        self.assertEqual(pkg.test_cases[0].code, "CBC")
        self.assertEqual(pkg.test_cases[1].code, "LIPID")

        # Verify schema serialization
        read_model = PackageWithTestsRead.model_validate(pkg)
        self.assertEqual(read_model.test_count, 2)
        self.assertEqual(len(read_model.test_cases), 2)

    def test_02_create_package_duplicate_code(self):
        payload = PackageCreate(
            name="Package Alpha",
            code="PKG-DUP",
            price=Decimal("500.00"),
            test_case_ids=[self.test1.id],
        )
        packages.create_package(payload=payload, db=self.db, _=self.admin)

        with self.assertRaises(HTTPException) as ctx:
            packages.create_package(payload=payload, db=self.db, _=self.admin)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", ctx.exception.detail)

    def test_03_create_package_invalid_test_id(self):
        payload = PackageCreate(
            name="Invalid Test Package",
            code="PKG-INVALID",
            price=Decimal("500.00"),
            test_case_ids=[99999],
        )
        with self.assertRaises(HTTPException) as ctx:
            packages.create_package(payload=payload, db=self.db, _=self.admin)
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_04_create_package_with_inactive_test(self):
        payload = PackageCreate(
            name="Inactive Test Package",
            code="PKG-INACTIVE",
            price=Decimal("500.00"),
            test_case_ids=[self.test_inactive.id],
        )
        with self.assertRaises(HTTPException) as ctx:
            packages.create_package(payload=payload, db=self.db, _=self.admin)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("inactive", ctx.exception.detail.lower())

    def test_05_list_and_search_packages(self):
        # Create 2 packages
        packages.create_package(
            payload=PackageCreate(
                name="Cardiac Care Package",
                code="PKG-CARDIO",
                price=Decimal("999.00"),
                department_id=self.dept.id,
                test_case_ids=[self.test2.id],
            ),
            db=self.db,
            _=self.admin,
        )
        packages.create_package(
            payload=PackageCreate(
                name="Basic Blood Profile",
                code="PKG-BLOOD",
                price=Decimal("250.00"),
                test_case_ids=[self.test1.id],
            ),
            db=self.db,
            _=self.admin,
        )

        # List all
        all_pkgs = packages.list_packages(db=self.db, _=self.admin)
        self.assertEqual(len(all_pkgs), 2)

        # Search by code
        searched = packages.search_packages(db=self.db, _=self.admin, q="CARDIO")
        self.assertEqual(len(searched), 1)
        self.assertEqual(searched[0].code, "PKG-CARDIO")

        # Filter by department
        filtered = packages.list_packages(db=self.db, _=self.admin, department_id=self.dept.id)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].code, "PKG-CARDIO")

    def test_06_get_and_update_package(self):
        created = packages.create_package(
            payload=PackageCreate(
                name="Initial Package",
                code="PKG-INIT",
                price=Decimal("400.00"),
                test_case_ids=[self.test1.id],
            ),
            db=self.db,
            _=self.admin,
        )
        pkg_id = created.id

        # Get package
        pkg = packages.get_package(db=self.db, _=self.admin, package_id=pkg_id)
        self.assertEqual(pkg.name, "Initial Package")

        # Update package name, price, and add test2
        updated = packages.update_package(
            payload=PackageUpdate(
                name="Updated Package Name",
                price=Decimal("850.00"),
                test_case_ids=[self.test1.id, self.test2.id],
            ),
            db=self.db,
            _=self.admin,
            package_id=pkg_id,
        )
        self.assertEqual(updated.name, "Updated Package Name")
        self.assertEqual(updated.price, Decimal("850.00"))
        self.assertEqual(updated.test_count, 2)

    def test_07_deactivate_and_reactivate_package(self):
        created = packages.create_package(
            payload=PackageCreate(
                name="Deactivate Me",
                code="PKG-DEACT",
                price=Decimal("300.00"),
            ),
            db=self.db,
            _=self.admin,
        )
        pkg_id = created.id

        # Deactivate
        deact = packages.deactivate_package(db=self.db, _=self.admin, package_id=pkg_id)
        self.assertFalse(deact.is_active)

        # Active-only list should exclude it
        active_pkgs = packages.list_packages(db=self.db, _=self.admin, active_only=True)
        self.assertEqual(len(active_pkgs), 0)

        # Reactivate
        react = packages.reactivate_package(db=self.db, _=self.admin, package_id=pkg_id)
        self.assertTrue(react.is_active)

    def test_08_schema_code_validation(self):
        # Invalid code with spaces or lowercase should be normalized or rejected
        with self.assertRaises(ValidationError):
            PackageCreate(
                name="Test Code Validation",
                code="invalid code with spaces!",
                price=Decimal("100.00"),
            )
