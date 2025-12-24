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
    
    # Peer Classification fields (US-N9)
    peer_focus: Mapped[str | None] = mapped_column(String(100))  # Investment focus (exact copy of aimc_category)
    peer_currency: Mapped[str | None] = mapped_column(String(10))  # Base currency (THB, USD, etc.)
    peer_fx_hedged_flag: Mapped[str | None] = mapped_column(String(20))  # FX hedge status (Hedged, Unhedged, Mixed, Unknown)
    peer_distribution_policy: Mapped[str | None] = mapped_column(String(1))  # Distribution policy (D=Dividend, A=Accumulation)
    peer_key: Mapped[str | None] = mapped_column(String(500))  # Computed peer group key
    peer_key_fallback_level: Mapped[int] = mapped_column(Integer, default=0)  # Fallback level (0=full, 1=dropped dist, 2=dropped hedge, 3=AIMC-only)
    
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
        Index("idx_fund_peer_key", "peer_key"),  # For peer group membership queries (partial index on non-NULL)
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


class SwitchPreviewLog(Base):
    """Switch preview log for tracking preview requests."""
    
    __tablename__ = "switch_preview_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    current_fund_id: Mapped[str] = mapped_column(String(50), nullable=False)
    target_fund_id: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_thb: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deltas_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # Stored Deltas as JSON
    missing_flags_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # Stored missing flags as JSON
    data_snapshot_id: Mapped[str | None] = mapped_column(String(50))  # Data snapshot ID for freshness tracking
    
    __table_args__ = (
        Index("idx_switch_preview_log_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<SwitchPreviewLog {self.id}: {self.current_fund_id} -> {self.target_fund_id} ({self.amount_thb} THB)>"


class FundReturnSnapshot(Base):
    """Fund return snapshot for performance tracking and peer comparisons."""
    
    __tablename__ = "fund_return_snapshot"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Note: No foreign key constraint because fund table has composite primary key
    # (proj_id, class_abbr_name), so proj_id alone is not unique
    proj_id: Mapped[str] = mapped_column(String(50), nullable=False)
    class_abbr_name: Mapped[str] = mapped_column(String(50), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    ytd_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    trailing_1y_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    trailing_3y_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    trailing_5y_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    eligible_1y: Mapped[bool] = mapped_column(default=False)
    eligible_3y: Mapped[bool] = mapped_column(default=False)
    eligible_5y: Mapped[bool] = mapped_column(default=False)
    data_source: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("proj_id", "class_abbr_name", "as_of_date", name="uq_fund_return_snapshot"),
        Index("idx_fund_return_snapshot_lookup", "proj_id", "class_abbr_name", "as_of_date"),
        Index("idx_fund_return_snapshot_date", "as_of_date"),
    )
    
    def __repr__(self) -> str:
        class_info = f" ({self.class_abbr_name})" if self.class_abbr_name else ""
        return f"<FundReturnSnapshot {self.proj_id}{class_info}: {self.as_of_date}>"
