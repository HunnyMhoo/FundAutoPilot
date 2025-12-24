"""
Migration script to add peer classification columns to fund table.

Usage:
    python -m app.services.ingestion.migrate_peer_classification_columns
"""

import logging
from sqlalchemy import text
from app.core.database import SyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def migrate():
    """Add peer classification columns to fund table."""
    with SyncSessionLocal() as session:
        logger.info("Adding peer classification columns to fund table...")
        
        # Add columns if they don't exist
        columns_to_add = [
            ("peer_focus", "VARCHAR(100)", "Investment focus (exact copy of aimc_category)"),
            ("peer_currency", "VARCHAR(10)", "Base currency (THB, USD, etc.)"),
            ("peer_fx_hedged_flag", "VARCHAR(20)", "FX hedge status (Hedged, Unhedged, Mixed, Unknown)"),
            ("peer_distribution_policy", "VARCHAR(1)", "Distribution policy (D=Dividend, A=Accumulation)"),
            ("peer_key", "VARCHAR(500)", "Computed peer group key"),
            ("peer_key_fallback_level", "INTEGER", "Fallback level applied (0=full, 1=dropped dist, 2=dropped hedge, 3=AIMC-only)"),
        ]
        
        for col_name, col_type, description in columns_to_add:
            try:
                # Check if column exists
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'fund' AND column_name = :col_name
                """)
                result = session.execute(check_query, {"col_name": col_name})
                if result.fetchone():
                    logger.info(f"  ⊙ Column {col_name} already exists, skipping")
                else:
                    session.execute(text(f"""
                        ALTER TABLE fund ADD COLUMN {col_name} {col_type}
                    """))
                    session.commit()
                    logger.info(f"  ✓ Added column: {col_name} - {description}")
            except Exception as e:
                logger.warning(f"  ⊙ Error adding column {col_name}: {e}")
                session.rollback()
        
        # Set default value for peer_key_fallback_level
        try:
            session.execute(text("""
                ALTER TABLE fund 
                ALTER COLUMN peer_key_fallback_level SET DEFAULT 0
            """))
            session.commit()
            logger.info("  ✓ Set default value for peer_key_fallback_level")
        except Exception as e:
            logger.warning(f"  ⊙ Error setting default: {e}")
            session.rollback()
        
        # Add index for peer_key (partial index for non-NULL values)
        try:
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fund_peer_key 
                ON fund(peer_key) 
                WHERE peer_key IS NOT NULL
            """))
            session.commit()
            logger.info("  ✓ Created index: idx_fund_peer_key")
        except Exception as e:
            logger.warning(f"  ⊙ Index may already exist: {e}")
            session.rollback()
        
        logger.info("=" * 60)
        logger.info("PEER CLASSIFICATION MIGRATION COMPLETE")
        logger.info("=" * 60)


if __name__ == "__main__":
    migrate()

