from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TestCategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Category name cannot be blank")
        return cleaned


class TestCategoryCreate(TestCategoryBase):
    pass


class TestCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Category name cannot be blank")
            return cleaned
        return v


class TestCategoryRead(TestCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class TestMasterBase(BaseModel):
    category_id: int | None = None
    test_code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=255)
    price: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)
    sample_type: str | None = Field(default=None, max_length=100)
    turnaround_time_hours: int = Field(default=24, ge=1, le=720)
    is_active: bool = True

    @field_validator("test_code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Test code cannot be blank")
        return cleaned

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Test name cannot be blank")
        return cleaned


class TestMasterCreate(TestMasterBase):
    pass


class TestMasterUpdate(BaseModel):
    category_id: int | None = None
    test_code: str | None = Field(default=None, min_length=2, max_length=50)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    price: Decimal | None = Field(default=None, ge=Decimal("0.00"), decimal_places=2)
    sample_type: str | None = Field(default=None, max_length=100)
    turnaround_time_hours: int | None = Field(default=None, ge=1, le=720)
    is_active: bool | None = None

    @field_validator("test_code")
    @classmethod
    def normalize_code(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip().upper()
            if not cleaned:
                raise ValueError("Test code cannot be blank")
            return cleaned
        return v

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Test name cannot be blank")
            return cleaned
        return v


class TestMasterRead(TestMasterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: TestCategoryRead | None = None
    created_at: datetime
    updated_at: datetime
