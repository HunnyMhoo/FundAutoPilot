"""SQLAlchemy ORM models for Fund and AMC tables."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Date, DateTime, Numeric, ForeignKey, Index
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
    
    def __repr__(self) -> str:
        return f"<AMC {self.unique_id}: {self.name_en}>"


class Fund(Base):
    """Mutual Fund model."""
    
    __tablename__ = "fund"
    
    proj_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    fund_name_th: Mapped[str | None] = mapped_column(String(500))
    fund_name_en: Mapped[str] = mapped_column(String(500), nullable=False)
    fund_abbr: Mapped[str | None] = mapped_column(String(50))
    amc_id: Mapped[str] = mapped_column(
        String(20), 
        ForeignKey("amc.unique_id"),
        nullable=False
    )
    fund_status: Mapped[str] = mapped_column(String(10), nullable=False)
    regis_date: Mapped[date | None] = mapped_column(Date)
    category: Mapped[str | None] = mapped_column(String(100))
    risk_level: Mapped[str | None] = mapped_column(String(20))
    expense_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    last_upd_date: Mapped[datetime | None] = mapped_column(DateTime)
    data_snapshot_id: Mapped[str | None] = mapped_column(String(50))
    
    # Relationship
    amc: Mapped["AMC"] = relationship("AMC", back_populates="funds")
    
    # Indexes for efficient pagination
    __table_args__ = (
        Index("idx_fund_name_asc", "fund_name_en", "proj_id"),
        Index("idx_fund_status", "fund_status"),
    )
    
    def __repr__(self) -> str:
        return f"<Fund {self.proj_id}: {self.fund_abbr}>"
