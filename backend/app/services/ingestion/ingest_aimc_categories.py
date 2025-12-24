"""
Ingest AIMC classification data from CSV and SEC API.

This script:
1. Loads AIMC CSV (primary source) - matched by fund abbreviation
2. Loads SEC API fund_compare codes (fallback) - matched by proj_id
3. Stores both with source tracking for display

Display logic:
- aimc_category: Display value (AIMC CSV category or mapped SEC code)
- aimc_code: Raw SEC API code (for reference)
- aimc_category_source: 'AIMC_CSV' or 'SEC_API'

Usage:
    python -m app.services.ingestion.ingest_aimc_categories --csv /path/to/aimc.csv
"""

import csv
import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime

from sqlalchemy import text
from app.core.database import SyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# SEC API code to AIMC category mapping (for fallback display)
SEC_CODE_TO_CATEGORY = {
    # Thai Equity
    'EG': 'Equity General',
    'SET50': 'SET 50 Index Fund',
    'ESMP': 'Equity Small - Mid Cap',
    'ELCE': 'Equity Large Cap',
    
    # Regional Equity
    'USEQ': 'US Equity',
    'JPEQ': 'Japan Equity',
    'EUEQ': 'European Equity',
    'CHEQ': 'Greater China Equity',
    'EQCHA': 'China Equity - A Shares',
    'AEJ': 'Asia Pacific Ex Japan',
    'IDEQ': 'India Equity',
    'VIEQ': 'Vietnam Equity',
    'ASEQ': 'ASEAN Equity',
    
    # Global Equity
    'GLEQ': 'Global Equity',
    'GEEQ': 'Emerging Market',
    'EQGLOTH': 'Other Global Sector Equity',
    'EQGLH': 'Global Equity Fully FX Risk Hedge',
    'EQGLINFRA': 'Global Equity - Infrastructure',
    'EQGLAENG': 'Global Equity - Alternative Energy',
    'EQGLCGNS': 'Global Equity - Consumer Goods and Services',
    
    # Sector Equity
    'TECHEQ': 'Technology Equity',
    'HCS': 'Health Care',
    'CE': 'Commodities Energy',
    'ENG': 'Energy',
    
    # Fixed Income
    'STGB': 'Short Term General Bond',
    'MTGB': 'Mid Term General Bond',
    'LTGB': 'Long Term General Bond',
    'GBD': 'Global Bond Discretionary F/X Hedge or Unhedge',
    'GBF': 'Global Bond Fully F/X Hedge',
    'EMBD': 'Emerging Market Bond Discretionary F/X Hedge or Unhedge',
    'HYB': 'High Yield Bond',
    'STGOV': 'Short Term Government Bond',
    'MTGOV': 'Mid Term Government Bond',
    
    # Money Market
    'MMGOV': 'Money Market Government',
    'MMG': 'Money Market General',
    
    # Mixed/Allocation
    'AA': 'Aggressive Allocation',
    'MA': 'Moderate Allocation',
    'CA': 'Conservative Allocation',
    'FIA': 'Foreign Investment Allocation',
    'MIS': 'Miscellaneous',
    
    # Property/REITs
    'FF': 'Fund of Property Fund - Foreign',
    'FFT': 'Fund of Property Fund - Thai',
    'FPF': 'Fund of Property fund -Thai and Foreign',
    
    # Commodities
    'CPM': 'Commodities Precious Metals',
}


def load_aimc_csv(csv_path: str) -> dict[str, str]:
    """Load AIMC CSV and return fund_code -> category mapping."""
    aimc_lookup = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fund_code = row['Fund Code'].strip()
            category = row['AIMC Category'].strip()
            aimc_lookup[fund_code] = category
    logger.info(f"Loaded {len(aimc_lookup)} fund codes from AIMC CSV")
    return aimc_lookup


def load_sec_api_codes(raw_data_path: str) -> dict[str, str]:
    """Load SEC API fund_compare codes from raw data file."""
    sec_lookup = {}
    with open(raw_data_path, 'r') as f:
        data = json.load(f)
    
    for proj_id, fund_info in data.get('funds', {}).items():
        code = fund_info.get('aimc_code')
        if code:
            sec_lookup[proj_id] = code
    
    logger.info(f"Loaded {len(sec_lookup)} SEC API codes")
    return sec_lookup


def normalize_fund_abbr(abbr: str) -> str:
    """Normalize fund abbreviation for matching."""
    return re.sub(r'[-\s]', '', abbr.upper())


def ingest_aimc_data(aimc_csv_path: str, sec_raw_path: str | None = None):
    """
    Ingest AIMC classification data into database.
    
    Args:
        aimc_csv_path: Path to AIMC CSV file
        sec_raw_path: Path to SEC API raw data JSON (optional)
    """
    # Load data sources
    aimc_lookup = load_aimc_csv(aimc_csv_path)
    aimc_normalized = {normalize_fund_abbr(k): v for k, v in aimc_lookup.items()}
    
    sec_lookup = {}
    if sec_raw_path and Path(sec_raw_path).exists():
        sec_lookup = load_sec_api_codes(sec_raw_path)
    
    # Get all funds from database
    with SyncSessionLocal() as session:
        result = session.execute(text('''
            SELECT proj_id, class_abbr_name, fund_abbr
            FROM fund 
            WHERE fund_status = 'RG'
        '''))
        funds = result.fetchall()
    
    logger.info(f"Processing {len(funds)} funds...")
    
    # Process and categorize
    stats = {
        'aimc_csv_match': 0,
        'sec_api_fallback': 0,
        'no_match': 0,
    }
    
    updates = []
    for proj_id, class_abbr_name, fund_abbr in funds:
        aimc_category = None
        aimc_code = sec_lookup.get(proj_id)  # Always store SEC code if available
        source = None
        
        # Strategy 1: Direct match with AIMC CSV
        if fund_abbr and fund_abbr in aimc_lookup:
            aimc_category = aimc_lookup[fund_abbr]
            source = 'AIMC_CSV'
            stats['aimc_csv_match'] += 1
        # Strategy 2: Normalized match with AIMC CSV
        elif fund_abbr:
            norm_key = normalize_fund_abbr(fund_abbr)
            if norm_key in aimc_normalized:
                aimc_category = aimc_normalized[norm_key]
                source = 'AIMC_CSV'
                stats['aimc_csv_match'] += 1
        
        # Strategy 3: Fallback to SEC API code mapping
        if not aimc_category and aimc_code:
            mapped_category = SEC_CODE_TO_CATEGORY.get(aimc_code)
            if mapped_category:
                aimc_category = mapped_category
                source = 'SEC_API'
                stats['sec_api_fallback'] += 1
        
        if not aimc_category:
            stats['no_match'] += 1
        
        updates.append({
            'proj_id': proj_id,
            'class_abbr_name': class_abbr_name,
            'aimc_category': aimc_category,
            'aimc_code': aimc_code,
            'aimc_category_source': source,
        })
    
    # Batch update database
    logger.info("Updating database...")
    with SyncSessionLocal() as session:
        for update in updates:
            session.execute(text('''
                UPDATE fund 
                SET aimc_category = :aimc_category,
                    aimc_code = :aimc_code,
                    aimc_category_source = :aimc_category_source
                WHERE proj_id = :proj_id AND class_abbr_name = :class_abbr_name
            '''), update)
        session.commit()
    
    # Print summary
    total = len(funds)
    logger.info("=" * 60)
    logger.info("AIMC INGESTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total funds processed: {total}")
    logger.info(f"AIMC CSV match: {stats['aimc_csv_match']} ({stats['aimc_csv_match']/total*100:.1f}%)")
    logger.info(f"SEC API fallback: {stats['sec_api_fallback']} ({stats['sec_api_fallback']/total*100:.1f}%)")
    logger.info(f"No match: {stats['no_match']} ({stats['no_match']/total*100:.1f}%)")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingest AIMC classification data")
    parser.add_argument('--csv', required=True, help="Path to AIMC CSV file")
    parser.add_argument('--sec-raw', help="Path to SEC API raw data JSON (optional)")
    args = parser.parse_args()
    
    # Default SEC raw data path
    sec_raw_path = args.sec_raw
    if not sec_raw_path:
        # Try to find the most recent raw data file
        data_dir = Path(__file__).parent.parent.parent.parent / "data" / "aimc_codes"
        raw_files = list(data_dir.glob("aimc_codes_raw_*.json"))
        if raw_files:
            sec_raw_path = str(sorted(raw_files)[-1])  # Most recent
            logger.info(f"Using SEC raw data: {sec_raw_path}")
    
    ingest_aimc_data(args.csv, sec_raw_path)


if __name__ == "__main__":
    main()

