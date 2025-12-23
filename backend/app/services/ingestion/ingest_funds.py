"""
SEC Thailand Fund Data Ingestion Script

Fetches all mutual fund data from SEC Thailand API and stores in database.

Usage:
    python -m app.services.ingestion.ingest_funds

Environment variables required:
    DATABASE_URL: PostgreSQL connection string
    SEC_FUND_FACTSHEET_API_KEY: API key for Fund Factsheet API
"""

import time
import logging
from datetime import datetime
from typing import Any

import requests
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.database import sync_engine, SyncSessionLocal, Base
from app.models.fund_orm import AMC, Fund

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
SEC_API_BASE = "https://api.sec.or.th/FundFactsheet"
RATE_LIMIT_DELAY = 0.1  # 100ms between requests (safe for 3000/300s limit)


class SECFundIngester:
    """Ingests fund data from SEC Thailand API into database."""
    
    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.settings.sec_fund_factsheet_api_key
        }
        self.snapshot_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.stats = {
            "amcs_fetched": 0,
            "amcs_stored": 0,
            "funds_fetched": 0,
            "funds_active": 0,
            "funds_stored": 0,
            "errors": 0,
        }
    
    def fetch_amcs(self) -> list[dict[str, Any]]:
        """Fetch all Asset Management Companies from SEC API."""
        url = f"{SEC_API_BASE}/fund/amc"
        logger.info(f"Fetching AMCs from {url}")
        
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        
        amcs = response.json()
        self.stats["amcs_fetched"] = len(amcs)
        logger.info(f"Fetched {len(amcs)} AMCs")
        
        return amcs
    
    def fetch_funds_for_amc(self, amc_id: str) -> list[dict[str, Any]]:
        """Fetch all funds for a specific AMC."""
        url = f"{SEC_API_BASE}/fund/amc/{amc_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching funds for AMC {amc_id}: {e}")
            self.stats["errors"] += 1
            return []
    
    def store_amcs(self, session, amcs: list[dict[str, Any]]) -> None:
        """Upsert AMCs into database."""
        for amc_data in amcs:
            stmt = insert(AMC).values(
                unique_id=amc_data["unique_id"],
                name_th=amc_data.get("name_th"),
                name_en=amc_data.get("name_en", "Unknown"),
                last_upd_date=self._parse_datetime(amc_data.get("last_upd_date")),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["unique_id"],
                set_={
                    "name_th": stmt.excluded.name_th,
                    "name_en": stmt.excluded.name_en,
                    "last_upd_date": stmt.excluded.last_upd_date,
                }
            )
            session.execute(stmt)
        
        session.commit()
        self.stats["amcs_stored"] = len(amcs)
        logger.info(f"Stored {len(amcs)} AMCs")
    
    def store_funds(self, session, funds: list[dict[str, Any]], amc_id: str) -> int:
        """Upsert active funds into database. Returns count stored."""
        stored = 0
        
        for fund_data in funds:
            # Only store active (RG) funds
            if fund_data.get("fund_status") != "RG":
                continue
            
            stmt = insert(Fund).values(
                proj_id=fund_data["proj_id"],
                fund_name_th=fund_data.get("proj_name_th"),
                fund_name_en=fund_data.get("proj_name_en", fund_data.get("proj_name_th", "Unknown")),
                fund_abbr=fund_data.get("proj_abbr_name"),
                amc_id=amc_id,
                fund_status=fund_data["fund_status"],
                regis_date=self._parse_date(fund_data.get("regis_date")),
                category=self._infer_category(fund_data),
                risk_level=None,  # Not available from this API
                expense_ratio=None,  # Would require per-fund API call
                last_upd_date=self._parse_datetime(fund_data.get("last_upd_date")),
                data_snapshot_id=self.snapshot_id,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["proj_id"],
                set_={
                    "fund_name_th": stmt.excluded.fund_name_th,
                    "fund_name_en": stmt.excluded.fund_name_en,
                    "fund_abbr": stmt.excluded.fund_abbr,
                    "fund_status": stmt.excluded.fund_status,
                    "regis_date": stmt.excluded.regis_date,
                    "category": stmt.excluded.category,
                    "last_upd_date": stmt.excluded.last_upd_date,
                    "data_snapshot_id": stmt.excluded.data_snapshot_id,
                }
            )
            session.execute(stmt)
            stored += 1
        
        return stored
    
    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse datetime from SEC API format."""
        if not value or value == "-":
            return None
        try:
            # Handle format like "2025-12-23T07:12:23.45"
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    def _parse_date(self, value: str | None):
        """Parse date from SEC API format."""
        if not value or value == "-":
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    
    def _infer_category(self, fund_data: dict[str, Any]) -> str | None:
        """Infer category from fund name or other fields."""
        name = (fund_data.get("proj_name_en") or "").lower()
        
        # Simple keyword-based categorization
        if "equity" in name or "stock" in name or "หุ้น" in fund_data.get("proj_name_th", ""):
            return "Equity"
        elif "fixed income" in name or "bond" in name or "ตราสารหนี้" in fund_data.get("proj_name_th", ""):
            return "Fixed Income"
        elif "money market" in name or "ตลาดเงิน" in fund_data.get("proj_name_th", ""):
            return "Money Market"
        elif "mixed" in name or "balanced" in name or "ผสม" in fund_data.get("proj_name_th", ""):
            return "Mixed"
        elif "property" in name or "reit" in name:
            return "Property/REIT"
        elif "gold" in name or "ทองคำ" in fund_data.get("proj_name_th", ""):
            return "Commodity"
        elif "foreign" in name or "global" in name or "ต่างประเทศ" in fund_data.get("proj_name_th", ""):
            return "Foreign Investment"
        
        return None  # Unknown category
    
    def run(self) -> dict[str, int]:
        """Execute the full ingestion process."""
        start_time = time.time()
        logger.info(f"Starting fund ingestion (snapshot: {self.snapshot_id})")
        
        # Create tables if they don't exist
        Base.metadata.create_all(sync_engine)
        
        with SyncSessionLocal() as session:
            # Step 1: Fetch and store AMCs
            amcs = self.fetch_amcs()
            self.store_amcs(session, amcs)
            
            # Step 2: Fetch and store funds for each AMC
            for i, amc in enumerate(amcs):
                amc_id = amc["unique_id"]
                amc_name = amc.get("name_en", amc_id)[:40]
                
                logger.info(f"[{i+1}/{len(amcs)}] Fetching funds for {amc_name}...")
                
                time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
                funds = self.fetch_funds_for_amc(amc_id)
                
                self.stats["funds_fetched"] += len(funds)
                active_count = sum(1 for f in funds if f.get("fund_status") == "RG")
                self.stats["funds_active"] += active_count
                
                stored = self.store_funds(session, funds, amc_id)
                self.stats["funds_stored"] += stored
                
                session.commit()
                
                logger.info(f"  -> {len(funds)} total, {active_count} active, {stored} stored")
        
        duration = time.time() - start_time
        
        # Final summary
        logger.info("=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info(f"  Snapshot ID: {self.snapshot_id}")
        logger.info(f"  Duration: {duration:.1f} seconds")
        logger.info(f"  AMCs: {self.stats['amcs_stored']}")
        logger.info(f"  Funds fetched: {self.stats['funds_fetched']}")
        logger.info(f"  Active funds: {self.stats['funds_active']}")
        logger.info(f"  Funds stored: {self.stats['funds_stored']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 60)
        
        return self.stats


def main():
    """Entry point for ingestion script."""
    ingester = SECFundIngester()
    stats = ingester.run()
    return stats


if __name__ == "__main__":
    main()
