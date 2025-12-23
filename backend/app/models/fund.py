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


class FundDetail(BaseModel):
    """Detailed fund information for detail view."""
    
    fund_id: str = Field(..., description="Unique fund identifier (proj_id)")
    fund_name: str = Field(..., description="Fund name in English")
    fund_abbr: str | None = Field(None, description="Fund abbreviation")
    category: str | None = Field(None, description="Fund category/type")
    amc_id: str = Field(..., description="Asset Management Company ID")
    amc_name: str = Field(..., description="Asset Management Company name")
    risk_level: str | None = Field(None, description="Risk level (1-8 or descriptive)")
    expense_ratio: float | None = Field(None, description="Annual expense ratio percentage (rounded to 3 decimals)")
    as_of_date: str | None = Field(None, description="Data snapshot date (ISO format)")
    last_updated_at: str | None = Field(None, description="Last update timestamp (ISO format)")
    data_source: str | None = Field(None, description="Data source identifier")
    data_version: str | None = Field(None, description="Data version identifier")
    
    class Config:
        from_attributes = True


# Filter metadata models for US-N3
class CategoryItem(BaseModel):
    """Category filter option with count."""
    value: str = Field(..., description="Category name")
    count: int = Field(..., description="Number of funds in this category")


class RiskItem(BaseModel):
    """Risk level filter option with count."""
    value: str = Field(..., description="Risk level (1-8 or descriptive)")
    count: int = Field(..., description="Number of funds with this risk level")


class AMCItem(BaseModel):
    """AMC filter option with count."""
    id: str = Field(..., description="AMC unique identifier")
    name: str = Field(..., description="AMC name")
    count: int = Field(..., description="Number of funds from this AMC")


class CategoryListResponse(BaseModel):
    """Response for category filter metadata."""
    items: list[CategoryItem] = Field(..., description="List of categories with counts")


class RiskListResponse(BaseModel):
    """Response for risk level filter metadata."""
    items: list[RiskItem] = Field(..., description="List of risk levels with counts")


class AMCListResponse(BaseModel):
    """Response for AMC filter metadata with pagination."""
    items: list[AMCItem] = Field(..., description="List of AMCs with counts")
    next_cursor: str | None = Field(
        None,
        description="Cursor for next page, null if end of results"
    )
