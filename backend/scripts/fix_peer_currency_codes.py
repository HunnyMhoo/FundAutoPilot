"""
Fix numeric currency codes in peer classification data.

The SEC API sometimes returns numeric currency codes (e.g., "0102500166") 
instead of currency abbreviations. This script fixes existing data by 
replacing numeric codes with "THB" (default for Thai funds).

Usage:
    python -m scripts.fix_peer_currency_codes
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import SyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fix_currency_codes():
    """Fix numeric currency codes in peer_currency field."""
    with SyncSessionLocal() as session:
        logger.info("=" * 60)
        logger.info("FIXING NUMERIC CURRENCY CODES")
        logger.info("=" * 60)
        
        # Count funds with numeric currency codes
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM fund 
            WHERE fund_status = 'RG' 
                AND peer_currency IS NOT NULL 
                AND peer_currency ~ '^[0-9]+$'
        """))
        count = result.scalar()
        logger.info(f"Found {count} funds with numeric currency codes")
        
        if count == 0:
            logger.info("No numeric currency codes found. Nothing to fix.")
            return
        
        # Update numeric currency codes to THB
        result = session.execute(text("""
            UPDATE fund 
            SET peer_currency = 'THB',
                peer_key = REPLACE(peer_key, peer_currency || '|', 'THB|')
            WHERE fund_status = 'RG' 
                AND peer_currency IS NOT NULL 
                AND peer_currency ~ '^[0-9]+$'
        """))
        updated = result.rowcount
        session.commit()
        
        logger.info(f"Updated {updated} funds: numeric currency codes → THB")
        logger.info("=" * 60)
        logger.info("FIX COMPLETE")
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        fix_currency_codes()
    except Exception as e:
        logger.error(f"Error fixing currency codes: {e}", exc_info=True)
        sys.exit(1)

