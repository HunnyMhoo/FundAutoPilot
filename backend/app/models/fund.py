"""Pydantic schemas for Fund API requests and responses."""

from datetime import datetime
from pydantic import BaseModel, Field


class FundSummary(BaseModel):
    """Summary of a fund for catalog listing."""
    
    fund_id: str = Field(..., description="Unique fund identifier (proj_id)")
    fund_name: str = Field(..., description="Fund name in English")
    amc_name: str = Field(..., description="Asset Management Company name")
    category: str | None = Field(None, description="Fund category/type")
    risk_level: str | None = Field(None, description="Risk level (1-8 or descriptive)")
    expense_ratio: float | None = Field(None, description="Annual expense ratio percentage")
    
    class Config:
        from_attributes = True


class FundListResponse(BaseModel):
    """Response for paginated fund list."""
    
    items: list[FundSummary] = Field(..., description="List of funds")
    next_cursor: str | None = Field(
        None, 
        description="Cursor for next page, null if end of results"
    )
    as_of_date: str = Field(..., description="Data freshness date (ISO format)")
    data_snapshot_id: str = Field(..., description="Unique identifier for this data snapshot")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "fund_id": "M0008_2537",
                        "fund_name": "THE RUANG KHAO 4 FUND",
                        "amc_name": "KASIKORN ASSET MANAGEMENT",
                        "category": "Equity",
                        "risk_level": "6",
                        "expense_ratio": 2.01
                    }
                ],
                "next_cursor": "eyJuIjoiVEhFIFJVQU5HIiwiaSI6Ik0wMDA4XzI1MzcifQ==",
                "as_of_date": "2024-12-23",
                "data_snapshot_id": "20241223070000"
            }
        }


class CursorData(BaseModel):
    """Internal cursor structure for keyset pagination."""
    
    n: str = Field(..., description="Last fund name")
    i: str = Field(..., description="Last fund ID")
