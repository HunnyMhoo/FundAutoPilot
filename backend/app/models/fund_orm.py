"""SQLAlchemy ORM models for Fund and AMC tables."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Date, DateTime, Numeric, Integer, ForeignKey, Index, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AMC(Base):
    """Asset Management Company model."""
    
    __tablename__ = "amc"
    
    unique_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name_th: Mapped[str | None] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    last_upd_date: Mapped[datetime | None] = mapped_column(DateTime)
    
    # Relationship
    funds: Mapped[list["Fund"]] = relationship("Fund", back_populates="amc")
    
    # Indexes for AMC name search (US-N3)
    __table_args__ = (
        Index("idx_amc_name_search", "name_en", "name_th"),  # For typeahead search
    )
    
    def __repr__(self) -> str:
        return f"<AMC {self.unique_id}: {self.name_en}>"


class Fund(Base):
    """Mutual Fund model.
    
    Supports share classes: funds with multiple share classes (e.g., K-INDIA-A(A), K-INDIA-A(D))
    are stored as separate records with the same proj_id but different class_abbr_name.
    """
    
    __tablename__ = "fund"
    
    proj_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    class_abbr_name: Mapped[str] = mapped_column(String(50), primary_key=True, default='')  # Share class identifier (empty string for funds without classes)
    fund_name_th: Mapped[str | None] = mapped_column(String(500))
    fund_name_en: Mapped[str] = mapped_column(String(500), nullable=False)
    fund_abbr: Mapped[str | None] = mapped_column(String(50))  # Display abbreviation (class name if class exists, otherwise fund abbreviation)
    amc_id: Mapped[str] = mapped_column(
        String(20), 
        ForeignKey("amc.unique_id"),
        nullable=False
    )
    fund_status: Mapped[str] = mapped_column(String(10), nullable=False)
    regis_date: Mapped[date | None] = mapped_column(Date)
    category: Mapped[str | None] = mapped_column(String(100))
    risk_level: Mapped[str | None] = mapped_column(String(20))  # Legacy field, kept for backward compatibility
    risk_level_int: Mapped[int | None] = mapped_column(Integer)  # Integer risk level (1-8) from SEC
    risk_level_desc: Mapped[str | None] = mapped_column(Text)  # Base64-decoded risk description
    risk_last_upd_date: Mapped[datetime | None] = mapped_column(DateTime)  # Last update date for risk data
    expense_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    expense_ratio_last_upd_date: Mapped[datetime | None] = mapped_column(DateTime)  # Last update date for expense ratio
    fee_data_raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Raw fee data from SEC API (for analysis)
    fee_data_last_upd_date: Mapped[datetime | None] = mapped_column(DateTime)  # When raw fee data was fetched
    last_upd_date: Mapped[datetime | None] = mapped_column(DateTime)
    
    # AIMC Classification fields
    aimc_category: Mapped[str | None] = mapped_column(String(100))  # Display category (from CSV or mapped SEC code)
    aimc_code: Mapped[str | None] = mapped_column(String(20))  # Raw SEC API fund_compare code
    aimc_category_source: Mapped[str | None] = mapped_column(String(20))  # Source: 'AIMC_CSV' or 'SEC_API'
    data_snapshot_id: Mapped[str | None] = mapped_column(String(50))
    data_source: Mapped[str | None] = mapped_column(String(20))  # Data source identifier (e.g., "SEC")
    
    # Normalized fields for search
    fund_name_norm: Mapped[str | None] = mapped_column(String(500))
    fund_abbr_norm: Mapped[str | None] = mapped_column(String(50))
    
    # Relationship
    amc: Mapped["AMC"] = relationship("AMC", back_populates="funds")
    
    # Indexes for efficient pagination and search
    __table_args__ = (
        Index("idx_fund_name_asc", "fund_name_en", "proj_id"),
        Index("idx_fund_status", "fund_status"),
        Index("idx_fund_search", "fund_name_norm", "fund_abbr_norm"),
        Index("idx_fund_class_abbr", "class_abbr_name"),  # For lookup by class name
        # Indexes for filter metadata aggregations (US-N3)
        Index("idx_fund_category", "fund_status", "category"),  # Composite for filtering + aggregation
        Index("idx_fund_risk", "fund_status", "risk_level"),    # Composite for filtering + aggregation (legacy)
        Index("idx_fund_risk_int", "fund_status", "risk_level_int"),  # Composite for filtering + aggregation (US-N4)
        Index("idx_fund_amc", "fund_status", "amc_id"),       # For AMC filtering and aggregation
        Index("idx_fund_aimc_category", "fund_status", "aimc_category"),  # For AIMC category filtering
    )
    
    def __repr__(self) -> str:
        class_info = f" ({self.class_abbr_name})" if self.class_abbr_name else ""
        return f"<Fund {self.proj_id}{class_info}: {self.fund_abbr}>"
    
    @property
    def display_id(self) -> str:
        """Get the display identifier for this fund (class name if exists, otherwise fund_abbr or proj_id)."""
        if self.class_abbr_name and self.class_abbr_name != '':
            return self.class_abbr_name
        return self.fund_abbr or self.proj_id
