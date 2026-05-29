from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ServiceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    duration_minutes: int = Field(ge=5, le=480)
    price: int = Field(ge=0, le=100_000_000)
    currency: str = Field(default="NGN", min_length=3, max_length=3)
    pricing_mode: str = Field(default="fixed", pattern="^(fixed|from|consultation)$")
    deposit_policy: str = Field(default="tenant_default", pattern="^(tenant_default|custom|disabled)$")
    deposit_amount: int | None = Field(default=None, ge=0, le=100_000_000)

    @model_validator(mode="after")
    def validate_deposit_amount(self) -> "ServiceCreateRequest":
        if self.deposit_policy == "custom" and self.deposit_amount is None:
            raise ValueError("deposit_amount is required when deposit_policy is custom")
        return self


class ServiceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    price: int | None = Field(default=None, ge=0, le=100_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    pricing_mode: str | None = Field(default=None, pattern="^(fixed|from|consultation)$")
    deposit_policy: str | None = Field(default=None, pattern="^(tenant_default|custom|disabled)$")
    deposit_amount: int | None = Field(default=None, ge=0, le=100_000_000)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_deposit_amount(self) -> "ServiceUpdateRequest":
        if self.deposit_policy == "custom" and self.deposit_amount is None:
            raise ValueError("deposit_amount is required when deposit_policy is custom")
        return self


class ServiceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    duration_minutes: int
    price: int
    currency: str
    pricing_mode: str
    deposit_policy: str
    deposit_amount: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}
