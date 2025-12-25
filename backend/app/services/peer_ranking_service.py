"""
Peer Ranking Service

Computes peer-relative rankings (percentile, rank, quartile) for funds
within their peer groups.

Usage:
    from app.services.peer_ranking_service import PeerRankingService
    from app.core.database import SyncSessionLocal
    from datetime import date
    
    with SyncSessionLocal() as session:
        service = PeerRankingService(session)
        result = service.compute_peer_rank("K-INDIA-A(A)", "1y", date(2025, 1, 15))
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select, desc
from sqlalchemy.orm import Session

from app.models.fund_orm import Fund, FundReturnSnapshot, PeerStats
from app.models.peer_ranking import PeerRankResult, UnavailableReason
from app.services.peer_stats_service import PeerStatsService, HORIZON_COLUMN_MAP, HORIZON_ELIGIBILITY_MAP
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PeerRankingService:
    """Service for computing peer-relative rankings."""
    
    def __init__(self, session: Session):
        """
        Initialize PeerRankingService.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self.peer_stats_service = PeerStatsService(session)
        self.settings = get_settings()
    
    def compute_peer_rank(
        self,
        fund_id: str,
        horizon: str,
        as_of_date: date,
        class_id: str | None = None,
    ) -> PeerRankResult:
        """
        Compute peer rank for a single fund/class.
        
        Args:
            fund_id: Fund identifier (class_abbr_name or proj_id)
            horizon: Return horizon ("ytd", "1y", "3y", "5y")
            as_of_date: As-of date for return data
            class_id: Optional explicit class identifier
            
        Returns:
            PeerRankResult with ranking data or unavailable_reason
        """
        if horizon not in HORIZON_COLUMN_MAP:
            raise ValueError(f"Invalid horizon: {horizon}")
        
        # Look up fund
        fund = self._get_fund(fund_id, class_id)
        if fund is None:
            return self._unavailable_result(
                as_of_date,
                UnavailableReason.RETURN_DATA_MISSING,
                    peer_key="",
            )
        
        # Check peer key
        if not fund.peer_key:
            return self._unavailable_result(
                as_of_date,
                UnavailableReason.PEER_KEY_MISSING,
                peer_key="",
            )
        
        # Get fund's return for this horizon
        fund_return = self._get_fund_return(
            fund.proj_id, fund.class_abbr_name, horizon, as_of_date
        )
        
        if fund_return is None:
            return self._unavailable_result(
                as_of_date,
                UnavailableReason.RETURN_DATA_MISSING,
                peer_key=fund.peer_key,
            )
        
        # Get peer stats
        peer_stats = self.peer_stats_service.get_latest_peer_stats(
            fund.peer_key, horizon, as_of_date
        )
        
        if peer_stats is None:
            # Try to compute on-demand
            logger.info(f"Computing peer stats on-demand for {fund.peer_key} {horizon}")
            stats_dict = self.peer_stats_service.compute_peer_stats(
                fund.peer_key, horizon, as_of_date
            )
            self.peer_stats_service.store_peer_stats(stats_dict)
            peer_stats = self.peer_stats_service.get_latest_peer_stats(
                fund.peer_key, horizon, as_of_date
            )
        
        if peer_stats is None:
            return self._unavailable_result(
                as_of_date,
                UnavailableReason.PEER_GROUP_NOT_FOUND,
                peer_key=fund.peer_key,
            )
        
        # Check if peer group has enough members
        if peer_stats.peer_count_eligible < self.settings.peer_min_count_hard:
            return PeerRankResult(
                percentile=None,
                rank=None,
                quartile=None,
                peer_count_eligible=peer_stats.peer_count_eligible,
                peer_count_total=peer_stats.peer_count_total,
                peer_median_return=float(peer_stats.peer_median_return) if peer_stats.peer_median_return else None,
                excess_vs_peer_median=None,
                peer_key=fund.peer_key,
                as_of_date=as_of_date,
                unavailable_reason=UnavailableReason.INSUFFICIENT_PEER_SET,
            )
        
        # Get returns list from stats_json
        stats_json = peer_stats.stats_json or {}
        returns_list = stats_json.get("returns", [])
        
        if not returns_list:
            return self._unavailable_result(
                as_of_date,
                UnavailableReason.PEER_GROUP_NOT_FOUND,
                peer_key=fund.peer_key,
                peer_stats=peer_stats,
            )
        
        # Compute rank (returns are sorted descending, best first)
        fund_return_float = float(fund_return)
        rank = self._compute_rank(fund_return_float, returns_list)
        
        # Compute percentile
        percentile = self._compute_percentile(rank, len(returns_list))
        
        # Compute quartile
        quartile = self._compute_quartile(percentile)
        
        # Compute excess vs median
        excess_vs_median = None
        if peer_stats.peer_median_return is not None:
            excess_vs_median = round(fund_return_float - float(peer_stats.peer_median_return), 4)
        
        return PeerRankResult(
            percentile=round(percentile, 2),
            rank=rank,
            quartile=quartile,
            peer_count_eligible=peer_stats.peer_count_eligible,
            peer_count_total=peer_stats.peer_count_total,
            peer_median_return=float(peer_stats.peer_median_return) if peer_stats.peer_median_return else None,
            excess_vs_peer_median=excess_vs_median,
            peer_key=fund.peer_key,
            as_of_date=as_of_date,
            unavailable_reason=None,
        )
    
    def compute_peer_ranks_batch(
        self,
        fund_ids: list[str],
        horizon: str,
        as_of_date: date,
    ) -> dict[str, PeerRankResult]:
        """
        Compute peer ranks for multiple funds efficiently.
        
        Caches peer stats lookups to avoid querying the same peer_key multiple times.
        
        Args:
            fund_ids: List of fund identifiers
            horizon: Return horizon
            as_of_date: As-of date
            
        Returns:
            Dictionary mapping fund_id to PeerRankResult
        """
        results = {}
        
        # Cache for peer stats (peer_key -> PeerStats)
        peer_stats_cache: dict[str, PeerStats | None] = {}
        
        for fund_id in fund_ids:
            try:
                # Look up fund
                fund = self._get_fund(fund_id)
                if fund is None:
                    results[fund_id] = self._unavailable_result(
                        as_of_date,
                        UnavailableReason.RETURN_DATA_MISSING,
                        peer_key="",
                    )
                    continue
                
                # Check peer key
                if not fund.peer_key:
                    results[fund_id] = self._unavailable_result(
                        as_of_date,
                        UnavailableReason.PEER_KEY_MISSING,
                        peer_key="",
                    )
                    continue
                
                # Get fund's return
                fund_return = self._get_fund_return(
                    fund.proj_id, fund.class_abbr_name, horizon, as_of_date
                )
                
                if fund_return is None:
                    results[fund_id] = self._unavailable_result(
                        as_of_date,
                        UnavailableReason.RETURN_DATA_MISSING,
                        peer_key=fund.peer_key,
                    )
                    continue
                
                # Get peer stats (with caching)
                if fund.peer_key not in peer_stats_cache:
                    peer_stats = self.peer_stats_service.get_latest_peer_stats(
                        fund.peer_key, horizon, as_of_date
                    )
                    if peer_stats is None:
                        # Compute on-demand
                        stats_dict = self.peer_stats_service.compute_peer_stats(
                            fund.peer_key, horizon, as_of_date
                        )
                        self.peer_stats_service.store_peer_stats(stats_dict)
                        peer_stats = self.peer_stats_service.get_latest_peer_stats(
                            fund.peer_key, horizon, as_of_date
                        )
                    peer_stats_cache[fund.peer_key] = peer_stats
                
                peer_stats = peer_stats_cache[fund.peer_key]
                
                if peer_stats is None:
                    results[fund_id] = self._unavailable_result(
                        as_of_date,
                        UnavailableReason.PEER_GROUP_NOT_FOUND,
                        peer_key=fund.peer_key,
                    )
                    continue
                
                # Check peer count
                if peer_stats.peer_count_eligible < self.settings.peer_min_count_hard:
                    results[fund_id] = PeerRankResult(
                        percentile=None,
                        rank=None,
                        quartile=None,
                        peer_count_eligible=peer_stats.peer_count_eligible,
                        peer_count_total=peer_stats.peer_count_total,
                        peer_median_return=float(peer_stats.peer_median_return) if peer_stats.peer_median_return else None,
                        excess_vs_peer_median=None,
                        peer_key=fund.peer_key,
                        as_of_date=as_of_date,
                        unavailable_reason=UnavailableReason.INSUFFICIENT_PEER_SET,
                    )
                    continue
                
                # Compute rank from returns list
                stats_json = peer_stats.stats_json or {}
                returns_list = stats_json.get("returns", [])
                
                if not returns_list:
                    results[fund_id] = self._unavailable_result(
                        as_of_date,
                        UnavailableReason.PEER_GROUP_NOT_FOUND,
                        peer_key=fund.peer_key,
                        peer_stats=peer_stats,
                    )
                    continue
                
                fund_return_float = float(fund_return)
                rank = self._compute_rank(fund_return_float, returns_list)
                percentile = self._compute_percentile(rank, len(returns_list))
                quartile = self._compute_quartile(percentile)
                
                excess_vs_median = None
                if peer_stats.peer_median_return is not None:
                    excess_vs_median = round(fund_return_float - float(peer_stats.peer_median_return), 4)
                
                results[fund_id] = PeerRankResult(
                    percentile=round(percentile, 2),
                    rank=rank,
                    quartile=quartile,
                    peer_count_eligible=peer_stats.peer_count_eligible,
                    peer_count_total=peer_stats.peer_count_total,
                    peer_median_return=float(peer_stats.peer_median_return) if peer_stats.peer_median_return else None,
                    excess_vs_peer_median=excess_vs_median,
                    peer_key=fund.peer_key,
                    as_of_date=as_of_date,
                    unavailable_reason=None,
                )
                
            except Exception as e:
                logger.error(f"Error computing peer rank for {fund_id}: {e}")
                results[fund_id] = self._unavailable_result(
                    as_of_date,
                    UnavailableReason.RETURN_DATA_MISSING,
                    peer_key="",
                )
        
        return results
    
    def _get_fund(
        self,
        fund_id: str,
        class_id: str | None = None,
    ) -> Fund | None:
        """Look up fund by ID (class_abbr_name or proj_id)."""
        # Try lookup by class_abbr_name first
        query = select(Fund).where(Fund.class_abbr_name == fund_id)
        result = self.session.execute(query)
        fund = result.scalar_one_or_none()
        
        if fund is None:
            # Try by proj_id with empty class
            query = select(Fund).where(
                and_(
                    Fund.proj_id == fund_id,
                    Fund.class_abbr_name == "",
                )
            )
            result = self.session.execute(query)
            fund = result.scalar_one_or_none()
        
        return fund
    
    def _get_fund_return(
        self,
        proj_id: str,
        class_abbr_name: str,
        horizon: str,
        as_of_date: date,
    ) -> Decimal | None:
        """Get fund's return for a specific horizon."""
        return_column = HORIZON_COLUMN_MAP[horizon]
        eligibility_column = HORIZON_ELIGIBILITY_MAP.get(horizon)
        
        # Normalize class_abbr_name: empty string, "main", and "Main" are equivalent
        # Some return snapshots use "main" or "Main" while Fund records use ""
        normalized_class = class_abbr_name if class_abbr_name else ""
        
        # Get latest snapshot at or before as_of_date
        # Try both the normalized class and "main"/"Main" if class is empty
        from sqlalchemy import or_
        
        class_conditions = [FundReturnSnapshot.class_abbr_name == normalized_class]
        if not normalized_class:
            # If class is empty, also try "main" and "Main" (common in return snapshots)
            class_conditions.append(FundReturnSnapshot.class_abbr_name == "main")
            class_conditions.append(FundReturnSnapshot.class_abbr_name == "Main")
        
        query = (
            select(FundReturnSnapshot)
            .where(
                and_(
                    FundReturnSnapshot.proj_id == proj_id,
                    or_(*class_conditions),
                    FundReturnSnapshot.as_of_date <= as_of_date,
                )
            )
            .order_by(desc(FundReturnSnapshot.as_of_date))
            .limit(1)
        )
        
        result = self.session.execute(query)
        snapshot = result.scalar_one_or_none()
        
        if snapshot is None:
            return None
        
        # Check eligibility (if applicable)
        if eligibility_column:
            is_eligible = getattr(snapshot, eligibility_column, False)
            if not is_eligible:
                return None
        
        return getattr(snapshot, return_column, None)
    
    def _compute_rank(
        self,
        fund_return: float,
        returns_list: list[float],
    ) -> int:
        """
        Compute rank within sorted returns list.
        
        Returns list is sorted descending (best return first).
        Rank is 1-indexed (rank 1 = best).
        For ties, assigns the same rank (e.g., two funds with same return both get rank 1).
        """
        # Find position in sorted list
        for i, r in enumerate(returns_list):
            if fund_return >= r:
                return i + 1
        return len(returns_list)
    
    def _compute_percentile(self, rank: int, total_count: int) -> float:
        """
        Compute percentile from rank.
        
        Formula: (1 - (rank-1)/(n-1)) * 100 for n>1
        Higher percentile = better performance
        """
        if total_count <= 1:
            return 50.0  # Single fund case
        
        return (1 - (rank - 1) / (total_count - 1)) * 100
    
    def _compute_quartile(self, percentile: float) -> str:
        """
        Compute quartile from percentile.
        
        Q1: percentile >= 75 (top 25%)
        Q2: 50 <= percentile < 75
        Q3: 25 <= percentile < 50
        Q4: percentile < 25 (bottom 25%)
        """
        if percentile >= 75:
            return "Q1"
        elif percentile >= 50:
            return "Q2"
        elif percentile >= 25:
            return "Q3"
        else:
            return "Q4"

    def _unavailable_result(
        self,
        as_of_date: date,
        reason: str,
        peer_key: str,
        peer_stats: PeerStats | None = None,
    ) -> PeerRankResult:
        """Create an unavailable PeerRankResult."""
        return PeerRankResult(
            percentile=None,
            rank=None,
            quartile=None,
            peer_count_eligible=peer_stats.peer_count_eligible if peer_stats else 0,
            peer_count_total=peer_stats.peer_count_total if peer_stats else 0,
            peer_median_return=float(peer_stats.peer_median_return) if peer_stats and peer_stats.peer_median_return else None,
            excess_vs_peer_median=None,
            peer_key=peer_key,
            as_of_date=as_of_date,
            unavailable_reason=reason,
        )
