"""
Populate Elasticsearch index from existing database funds.

This script reads all active funds from the database and indexes them to Elasticsearch.
It's useful for:
- Initial index population
- Re-indexing after schema changes
- Re-indexing after data updates

Usage:
    python backend/scripts/populate_elasticsearch_index.py [--limit N] [--dry-run] [--batch-size N]
    
Options:
    --limit N       Only process first N funds (for testing)
    --dry-run       Show what would be done without making changes
    --batch-size N  Number of funds to index per batch (default: 100)
"""

import sys
import argparse
import logging
import time
import asyncio
from typing import Optional

sys.path.insert(0, '.')

from sqlalchemy import select
from app.core.database import SyncSessionLocal
from app.models.fund_orm import Fund, AMC
from app.services.search.elasticsearch_backend import ElasticsearchSearchBackend
from app.core.elasticsearch import get_elasticsearch_client
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


def fund_to_es_document(fund: Fund, amc_name: str) -> dict:
    """Convert a Fund ORM object to an Elasticsearch document."""
    # Use class_abbr_name as fund_id if it exists and is not empty, otherwise use proj_id
    # This matches the logic in ingest_funds.py
    fund_id = fund.class_abbr_name if fund.class_abbr_name and fund.class_abbr_name.strip() else fund.proj_id
    
    # Calculate fee_band from expense_ratio
    # Same logic as FundService._calculate_fee_band
    fee_band = None
    if fund.expense_ratio is not None:
        ratio = float(fund.expense_ratio)
        if ratio <= 1.0:
            fee_band = "low"
        elif ratio <= 2.0:
            fee_band = "medium"
        else:
            fee_band = "high"
    
    # Convert risk_level to integer if it's a string
    risk_level_int = None
    if fund.risk_level:
        try:
            # Try to parse as integer directly
            risk_level_int = int(fund.risk_level)
        except (ValueError, TypeError):
            # If it's a string like "1", "2", etc., extract the number
            import re
            match = re.search(r'\d+', str(fund.risk_level))
            if match:
                risk_level_int = int(match.group())
    
    return {
        "fund_id": fund_id,
        "proj_id": fund.proj_id,
        "class_abbr_name": fund.class_abbr_name if fund.class_abbr_name else None,
        "fund_name": fund.fund_name_en or fund.fund_name_th or "Unknown",
        "fund_name_norm": fund.fund_name_norm or "",
        "fund_abbr": fund.fund_abbr or "",
        "fund_abbr_norm": fund.fund_abbr_norm or "",
        "amc_id": fund.amc_id,
        "amc_name": amc_name,
        "category": fund.category,
        "risk_level": fund.risk_level,
        "risk_level_int": risk_level_int,
        "expense_ratio": float(fund.expense_ratio) if fund.expense_ratio is not None else None,
        "fee_band": fee_band,
        "fund_status": fund.fund_status,
    }


def find_active_funds(session, limit: Optional[int] = None):
    """Find all active funds from the database."""
    query = (
        select(Fund, AMC.name_en)
        .join(AMC, Fund.amc_id == AMC.unique_id)
        .where(Fund.fund_status == "RG")
        .order_by(Fund.fund_name_en)
    )
    
    if limit:
        query = query.limit(limit)
    
    result = session.execute(query)
    return result.all()


async def populate_index(
    dry_run: bool = False,
    limit: Optional[int] = None,
    batch_size: int = 100
) -> dict:
    """Populate Elasticsearch index from database."""
    stats = {
        "total_funds": 0,
        "indexed": 0,
        "errors": 0,
        "start_time": time.time(),
    }
    
    if not settings.elasticsearch_enabled:
        logger.error("Elasticsearch is not enabled in settings")
        return stats
    
    # Initialize Elasticsearch backend
    search_backend = ElasticsearchSearchBackend(get_elasticsearch_client())
    
    try:
        # Initialize index
        logger.info("Initializing Elasticsearch index...")
        await search_backend.initialize_index()
        
        with SyncSessionLocal() as session:
            # Find all active funds
            logger.info("Fetching funds from database...")
            funds = find_active_funds(session, limit=limit)
            stats["total_funds"] = len(funds)
            
            if not funds:
                logger.warning("No active funds found in database")
                return stats
            
            logger.info(f"Found {stats['total_funds']} active fund(s) to index")
            
            if dry_run:
                logger.info("=" * 80)
                logger.info("DRY RUN MODE - No data will be indexed")
                logger.info("=" * 80)
                logger.info(f"Would index {stats['total_funds']} funds")
                return stats
            
            # Process in batches
            es_docs = []
            for i, (fund, amc_name) in enumerate(funds, 1):
                try:
                    es_doc = fund_to_es_document(fund, amc_name or "Unknown")
                    es_docs.append(es_doc)
                    
                    # Index in batches
                    if len(es_docs) >= batch_size:
                        # #region agent log
                        import json; log_data = {"location": "populate_elasticsearch_index.py:batch", "message": "Indexing batch", "data": {"batch_size": len(es_docs), "total_processed": i}, "timestamp": time.time(), "sessionId": "debug-session", "runId": "index-population", "hypothesisId": "index-population"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
                        # #endregion
                        await search_backend.bulk_index_funds(es_docs)
                        stats["indexed"] += len(es_docs)
                        logger.info(f"Indexed batch: {stats['indexed']}/{stats['total_funds']} funds")
                        es_docs = []
                except Exception as e:
                    logger.error(f"Error processing fund {fund.proj_id}/{fund.class_abbr_name}: {e}")
                    stats["errors"] += 1
                    # #region agent log
                    import json; log_data = {"location": "populate_elasticsearch_index.py:error", "message": "Error processing fund", "data": {"proj_id": fund.proj_id, "class_abbr_name": fund.class_abbr_name, "error": str(e)}, "timestamp": time.time(), "sessionId": "debug-session", "runId": "index-population", "hypothesisId": "index-population"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
                    # #endregion
            
            # Index remaining documents
            if es_docs:
                # #region agent log
                import json; log_data = {"location": "populate_elasticsearch_index.py:final_batch", "message": "Indexing final batch", "data": {"batch_size": len(es_docs)}, "timestamp": time.time(), "sessionId": "debug-session", "runId": "index-population", "hypothesisId": "index-population"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
                # #endregion
                await search_backend.bulk_index_funds(es_docs)
                stats["indexed"] += len(es_docs)
                logger.info(f"Indexed final batch: {stats['indexed']}/{stats['total_funds']} funds")
            
            # Verify index count
            try:
                from elasticsearch.exceptions import NotFoundError
                stats_result = await search_backend.client.indices.stats(index=search_backend.index_name)
                doc_count = stats_result["indices"][search_backend.index_name]["total"]["docs"]["count"]
                logger.info(f"Elasticsearch index now contains {doc_count} document(s)")
                # #region agent log
                import json; log_data = {"location": "populate_elasticsearch_index.py:complete", "message": "Index population completed", "data": {"total_funds": stats["total_funds"], "indexed": stats["indexed"], "errors": stats["errors"], "index_doc_count": doc_count}, "timestamp": time.time(), "sessionId": "debug-session", "runId": "index-population", "hypothesisId": "index-population"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
                # #endregion
            except (NotFoundError, KeyError) as e:
                logger.warning(f"Could not verify index count: {e}")
        
    except Exception as e:
        logger.error(f"Failed to populate Elasticsearch index: {e}")
        stats["errors"] += 1
        # #region agent log
        import json; log_data = {"location": "populate_elasticsearch_index.py:fatal_error", "message": "Fatal error during index population", "data": {"error": str(e), "error_type": type(e).__name__}, "timestamp": time.time(), "sessionId": "debug-session", "runId": "index-population", "hypothesisId": "index-population"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
    finally:
        # Close Elasticsearch connection
        try:
            await search_backend.client.close()
        except Exception as e:
            logger.warning(f"Error closing Elasticsearch connection: {e}")
    
    stats["duration_seconds"] = time.time() - stats["start_time"]
    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Populate Elasticsearch index from existing database funds"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process first N funds (for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of funds to index per batch (default: 100)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("ELASTICSEARCH INDEX POPULATION")
    logger.info("=" * 80)
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Limit: {args.limit or 'All funds'}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 80)
    
    # Run async function
    stats = asyncio.run(populate_index(
        dry_run=args.dry_run,
        limit=args.limit,
        batch_size=args.batch_size
    ))
    
    if not args.dry_run:
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total funds: {stats['total_funds']}")
        logger.info(f"Indexed: {stats['indexed']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Duration: {stats['duration_seconds']:.1f}s")
        logger.info("=" * 80)


if __name__ == "__main__":
    main()

