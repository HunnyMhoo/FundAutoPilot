"""
Bulk re-classification script for peer groups.

Re-classifies all funds in the database with peer group classification.

Usage:
    python -m scripts.reclassify_all_funds
    python -m scripts.reclassify_all_funds --batch-size 50
    python -m scripts.reclassify_all_funds --status RG
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SyncSessionLocal
from app.services.peer_classification_service import PeerClassificationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for bulk re-classification."""
    parser = argparse.ArgumentParser(description="Re-classify all funds with peer groups")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of funds to process per batch (default: 100)"
    )
    parser.add_argument(
        "--status",
        type=str,
        default="RG",
        help="Fund status to filter by (default: RG)"
    )
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("PEER CLASSIFICATION - BULK RE-CLASSIFICATION")
    logger.info("=" * 60)
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Fund status filter: {args.status}")
    logger.info("")
    
    service = PeerClassificationService()
    
    with SyncSessionLocal() as session:
        try:
            stats = service.classify_all_funds(
                session=session,
                batch_size=args.batch_size,
                fund_status=args.status
            )
            
            if "error" in stats:
                logger.error(f"Classification failed: {stats['error']}")
                sys.exit(1)
            
            logger.info("")
            logger.info("Re-classification complete!")
            
        except Exception as e:
            logger.error(f"Fatal error during re-classification: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()

