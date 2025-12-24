"""
Peer Classification Service

Computes and stores peer group classification for funds based on AIMC category,
currency, FX hedge flag, and distribution policy.

Usage:
    from app.services.peer_classification_service import PeerClassificationService
    from app.core.database import SyncSessionLocal
    from app.models.fund_orm import Fund
    
    with SyncSessionLocal() as session:
        fund = session.query(Fund).filter_by(proj_id='M0001_2024').first()
        service = PeerClassificationService()
        result = service.classify_fund(fund, session)
"""

import logging
from typing import Any
from collections import defaultdict, Counter

from sqlalchemy.orm import Session

from app.models.fund_orm import Fund
from app.utils.sec_api_client import SECAPIClient, SECAPIErrorType
from app.services.compare_service import select_default_class, filter_by_class

logger = logging.getLogger(__name__)


# FX hedge keyword patterns (exact substring matching in AIMC category name)
HEDGE_KEYWORD_PATTERNS = {
    "Fully FX Risk Hedge": "Hedged",
    "Fully F/X Hedge": "Hedged",
    "Discretionary F/X Hedge": "Mixed",
    "Discretionary F/X Hedge or Unhedge": "Mixed",
    "Unhedge": "Unhedged",
}

# Distribution policy mapping (SEC API dividend_policy field values)
# "Y" = pays dividends → "D" (Dividend)
# "N" = accumulating → "A" (Accumulation)
DISTRIBUTION_POLICY_MAPPING = {
    "Y": "D",  # Dividend
    "N": "A",  # Accumulation
}


class PeerClassificationService:
    """Service for computing peer group classifications."""
    
    def __init__(self):
        self.api_client = SECAPIClient()
    
    def compute_peer_focus(self, fund: Fund) -> str | None:
        """
        Compute peer focus (exact copy of aimc_category).
        
        Args:
            fund: Fund ORM object
            
        Returns:
            AIMC category value or None
        """
        return fund.aimc_category
    
    def compute_peer_currency(
        self, 
        proj_id: str, 
        class_abbr_name: str | None = None,
        fund_abbr: str | None = None
    ) -> str:
        """
        Compute peer currency from SEC API investment constraints.
        
        Args:
            proj_id: Fund project ID
            class_abbr_name: Optional share class abbreviation
            fund_abbr: Optional fund abbreviation for class selection
            
        Returns:
            Currency code (defaults to "THB" if not available)
        """
        try:
            data_list, error = self.api_client.fetch_investment(proj_id)
            if error or not data_list or len(data_list) == 0:
                return "THB"  # Default to THB
            
            # Select appropriate class if multiple classes exist
            selected_class = None
            if len(data_list) > 1:
                selected_class = select_default_class(fund_abbr, data_list)
            
            # Filter by selected class
            filtered_list = filter_by_class(data_list, selected_class)
            if not filtered_list:
                filtered_list = data_list  # Fallback to first item
            
            investment_data = filtered_list[0]
            
            # Try minimum_sub_cur first, then minimum_redempt_cur
            currency = investment_data.get("minimum_sub_cur") or investment_data.get("minimum_redempt_cur")
            
            if currency:
                # SEC API sometimes returns numeric currency codes (e.g., "0102500166")
                # If it's numeric, default to THB (most Thai funds use THB)
                if currency.isdigit():
                    logger.debug(f"Numeric currency code {currency} for {proj_id}, defaulting to THB")
                    return "THB"
                return currency.upper()  # Normalize to uppercase
            
            return "THB"  # Default to THB if not found
            
        except Exception as e:
            logger.warning(f"Error fetching currency for {proj_id}: {e}")
            return "THB"  # Default to THB on error
    
    def compute_peer_fx_hedged_flag(self, fund: Fund) -> str:
        """
        Compute FX hedge flag from AIMC category name using exact keyword matching.
        
        Args:
            fund: Fund ORM object
            
        Returns:
            Hedge flag: "Hedged", "Unhedged", "Mixed", or "Unknown"
        """
        if not fund.aimc_category:
            return "Unknown"
        
        category_name = fund.aimc_category
        
        # Check for exact keyword patterns (longest matches first)
        for keyword, flag in sorted(HEDGE_KEYWORD_PATTERNS.items(), key=len, reverse=True):
            if keyword in category_name:
                return flag
        
        return "Unknown"
    
    def compute_peer_distribution_policy(
        self,
        proj_id: str,
        class_abbr_name: str | None = None,
        fund_abbr: str | None = None
    ) -> str | None:
        """
        Compute distribution policy from SEC API dividend endpoint.
        
        Args:
            proj_id: Fund project ID
            class_abbr_name: Optional share class abbreviation
            fund_abbr: Optional fund abbreviation for class selection
            
        Returns:
            "D" (Dividend), "A" (Accumulation), or None if unavailable
        """
        try:
            data_list, error = self.api_client.fetch_dividend(proj_id)
            if error or not data_list or len(data_list) == 0:
                return None
            
            # Select appropriate class if multiple classes exist
            selected_class = None
            if len(data_list) > 1:
                selected_class = select_default_class(fund_abbr, data_list)
            
            # Filter by selected class
            filtered_list = filter_by_class(data_list, selected_class)
            if not filtered_list:
                filtered_list = data_list  # Fallback to first item
            
            dividend_data = filtered_list[0]
            dividend_policy = dividend_data.get("dividend_policy")
            
            if dividend_policy:
                # Map SEC API value to our code
                return DISTRIBUTION_POLICY_MAPPING.get(dividend_policy.upper())
            
            return None
            
        except Exception as e:
            logger.warning(f"Error fetching distribution policy for {proj_id}: {e}")
            return None
    
    def compute_peer_key(
        self,
        aimc_category: str | None,
        peer_focus: str | None,
        peer_currency: str | None,
        peer_fx_hedged_flag: str | None,
        peer_distribution_policy: str | None,
    ) -> str | None:
        """
        Compute peer key from classification components.
        
        Format: AIMC_TYPE|FOCUS|CURRENCY|HEDGE|DIST
        
        Args:
            aimc_category: AIMC category (mandatory)
            peer_focus: Investment focus (exact copy of aimc_category)
            peer_currency: Currency code
            peer_fx_hedged_flag: Hedge flag
            peer_distribution_policy: Distribution policy
            
        Returns:
            Peer key string or None if aimc_category is missing
        """
        if not aimc_category:
            return None
        
        # Use empty string for missing optional components
        focus = peer_focus or ""
        currency = peer_currency or ""
        hedge = peer_fx_hedged_flag or ""
        dist = peer_distribution_policy or ""
        
        # Build peer key: AIMC_TYPE|FOCUS|CURRENCY|HEDGE|DIST
        peer_key = f"{aimc_category}|{focus}|{currency}|{hedge}|{dist}"
        
        return peer_key
    
    def determine_fallback_level(
        self,
        peer_distribution_policy: str | None,
        peer_fx_hedged_flag: str | None,
        peer_currency: str | None,
    ) -> int:
        """
        Determine fallback level based on which dimensions are missing.
        
        Args:
            peer_distribution_policy: Distribution policy
            peer_fx_hedged_flag: Hedge flag
            peer_currency: Currency
            
        Returns:
            Fallback level: 0=full, 1=dropped dist, 2=dropped hedge, 3=AIMC-only
        """
        if not peer_distribution_policy:
            return 1  # Dropped distribution
        if not peer_fx_hedged_flag or peer_fx_hedged_flag == "Unknown":
            return 2  # Dropped hedge
        if not peer_currency:
            return 3  # AIMC-only (though currency should always default to THB)
        return 0  # Full classification
    
    def classify_fund(self, fund: Fund, session: Session) -> dict[str, Any]:
        """
        Classify a single fund and update database.
        
        Args:
            fund: Fund ORM object
            session: Database session
            
        Returns:
            Dictionary with classification results and stats
        """
        result = {
            "proj_id": fund.proj_id,
            "class_abbr_name": fund.class_abbr_name,
            "success": False,
            "peer_key": None,
            "fallback_level": 3,
        }
        
        try:
            # Compute classification components
            peer_focus = self.compute_peer_focus(fund)
            peer_currency = self.compute_peer_currency(
                fund.proj_id,
                fund.class_abbr_name,
                fund.fund_abbr
            )
            peer_fx_hedged_flag = self.compute_peer_fx_hedged_flag(fund)
            peer_distribution_policy = self.compute_peer_distribution_policy(
                fund.proj_id,
                fund.class_abbr_name,
                fund.fund_abbr
            )
            
            # Compute peer key
            peer_key = self.compute_peer_key(
                fund.aimc_category,
                peer_focus,
                peer_currency,
                peer_fx_hedged_flag,
                peer_distribution_policy,
            )
            
            # Determine fallback level
            fallback_level = self.determine_fallback_level(
                peer_distribution_policy,
                peer_fx_hedged_flag,
                peer_currency,
            )
            
            # Update fund record
            fund.peer_focus = peer_focus
            fund.peer_currency = peer_currency
            fund.peer_fx_hedged_flag = peer_fx_hedged_flag
            fund.peer_distribution_policy = peer_distribution_policy
            fund.peer_key = peer_key
            fund.peer_key_fallback_level = fallback_level
            
            session.commit()
            
            result.update({
                "success": True,
                "peer_focus": peer_focus,
                "peer_currency": peer_currency,
                "peer_fx_hedged_flag": peer_fx_hedged_flag,
                "peer_distribution_policy": peer_distribution_policy,
                "peer_key": peer_key,
                "fallback_level": fallback_level,
            })
            
            logger.debug(f"Classified {fund.proj_id}: {peer_key}")
            
        except Exception as e:
            logger.error(f"Error classifying fund {fund.proj_id}: {e}", exc_info=True)
            session.rollback()
            result["error"] = str(e)
        
        return result
    
    def classify_all_funds(
        self,
        session: Session,
        batch_size: int = 100,
        fund_status: str = "RG"
    ) -> dict[str, Any]:
        """
        Classify all funds in batches.
        
        Args:
            session: Database session
            batch_size: Number of funds to process per batch
            fund_status: Filter by fund status (default: "RG" for registered)
            
        Returns:
            Dictionary with classification statistics
        """
        stats = {
            "total_funds": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "with_peer_key": 0,
            "fallback_levels": defaultdict(int),
            "common_focus_values": defaultdict(int),
            "common_currencies": defaultdict(int),
            "common_hedge_flags": defaultdict(int),
            "common_distribution_policies": defaultdict(int),
        }
        
        try:
            # Query all active funds
            funds = session.query(Fund).filter(Fund.fund_status == fund_status).all()
            stats["total_funds"] = len(funds)
            
            logger.info(f"Classifying {stats['total_funds']} funds in batches of {batch_size}...")
            
            for i in range(0, len(funds), batch_size):
                batch = funds[i:i + batch_size]
                logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} funds)...")
                
                for fund in batch:
                    result = self.classify_fund(fund, session)
                    stats["processed"] += 1
                    
                    if result["success"]:
                        stats["successful"] += 1
                        
                        if result["peer_key"]:
                            stats["with_peer_key"] += 1
                            stats["fallback_levels"][result["fallback_level"]] += 1
                            
                            # Collect statistics
                            if result.get("peer_focus"):
                                stats["common_focus_values"][result["peer_focus"]] += 1
                            if result.get("peer_currency"):
                                stats["common_currencies"][result["peer_currency"]] += 1
                            if result.get("peer_fx_hedged_flag"):
                                stats["common_hedge_flags"][result["peer_fx_hedged_flag"]] += 1
                            if result.get("peer_distribution_policy"):
                                stats["common_distribution_policies"][result["peer_distribution_policy"]] += 1
                    else:
                        stats["failed"] += 1
                
                # Commit batch
                session.commit()
                logger.info(f"Batch {i // batch_size + 1} complete")
            
            # Calculate coverage percentage
            coverage_pct = (stats["with_peer_key"] / stats["total_funds"] * 100) if stats["total_funds"] > 0 else 0
            
            logger.info("=" * 60)
            logger.info("PEER CLASSIFICATION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Total funds: {stats['total_funds']}")
            logger.info(f"Processed: {stats['processed']}")
            logger.info(f"Successful: {stats['successful']}")
            logger.info(f"Failed: {stats['failed']}")
            logger.info(f"With peer key: {stats['with_peer_key']} ({coverage_pct:.1f}%)")
            logger.info(f"Fallback levels: {dict(stats['fallback_levels'])}")
            # Convert defaultdict to Counter for most_common() method
            focus_counter = Counter(stats['common_focus_values'])
            currency_counter = Counter(stats['common_currencies'])
            
            logger.info(f"Top focus values: {dict(focus_counter.most_common(10))}")
            logger.info(f"Top currencies: {dict(currency_counter.most_common(5))}")
            logger.info(f"Hedge flags: {dict(stats['common_hedge_flags'])}")
            logger.info(f"Distribution policies: {dict(stats['common_distribution_policies'])}")
            
        except Exception as e:
            logger.error(f"Error in bulk classification: {e}", exc_info=True)
            session.rollback()
            stats["error"] = str(e)
        
        return stats

