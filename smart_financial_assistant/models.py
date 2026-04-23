"""Pydantic request schemas for SIIGO financial report tool inputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrialBalanceRequest(BaseModel):
    """Input payload for querying SIIGO trial balance reports by account range."""

    account_start: str = Field(..., description="Cuenta inicial")
    account_end: str = Field(..., description="Cuenta final")
    year: int = Field(..., ge=2000, le=2100)
    month_start: int = Field(..., ge=1, le=13)
    month_end: int = Field(..., ge=1, le=13)
    includes_tax_difference: bool = Field(
        default=True,
        description="Incluir diferencia de impuestos",
    )


class TrialBalanceByThirdPartyRequest(TrialBalanceRequest):
    """Input payload for SIIGO trial balance grouped by third party."""

    includes_tax_difference: bool = False
