"""
Migration script to add AIMC classification columns to fund table.

Usage:
    python -m app.services.ingestion.migrate_aimc_columns
"""

import logging
from sqlalchemy import text
from app.core.database import SyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def migrate():
    """Add AIMC classification columns to fund table."""
    with SyncSessionLocal() as session:
        logger.info("Adding AIMC classification columns to fund table...")
        
        # Add columns if they don't exist
        columns_to_add = [
            ("aimc_category", "VARCHAR(100)"),
            ("aimc_code", "VARCHAR(20)"),
            ("aimc_category_source", "VARCHAR(20)"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                session.execute(text(f"""
                    ALTER TABLE fund ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """))
                logger.info(f"  Added column: {col_name}")
            except Exception as e:
                logger.warning(f"  Column {col_name} may already exist: {e}")
        
        # Add index for AIMC category filtering
        try:
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fund_aimc_category 
                ON fund (fund_status, aimc_category)
            """))
            logger.info("  Added index: idx_fund_aimc_category")
        except Exception as e:
            logger.warning(f"  Index may already exist: {e}")
        
        session.commit()
        logger.info("Migration complete!")


if __name__ == "__main__":
    migrate()

