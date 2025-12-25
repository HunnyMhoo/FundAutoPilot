"""
Peer Stats Service

Computes and retrieves peer group statistics for peer ranking.
Each share class is counted separately in peer groups.

Usage:
    from app.services.peer_stats_service import PeerStatsService
    from app.core.database import SyncSessionLocal
    from datetime import date
    
    with SyncSessionLocal() as session:
        service = PeerStatsService(session)
        stats = service.compute_peer_stats("Global Equity|US|USD|Hedged|D", "1y", date(2025, 1, 15))
"""

import logging
import statistics
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select, desc
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.fund_orm import Fund, FundReturnSnapshot, PeerStats
from app.services.peer_group_service import PeerGroupService
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Horizon to return column mapping
HORIZON_COLUMN_MAP = {
    "ytd": "ytd_return",
    "1y": "trailing_1y_return",
    "3y": "trailing_3y_return",
    "5y": "trailing_5y_return",
}

# Horizon to eligibility column mapping (YTD has no eligibility flag)
HORIZON_ELIGIBILITY_MAP = {
    "1y": "eligible_1y",
    "3y": "eligible_3y",
    "5y": "eligible_5y",
}


class PeerStatsService:
    """Service for computing and retrieving peer group statistics."""
    
    def __init__(self, session: Session):
        """
        Initialize PeerStatsService.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self.peer_group_service = PeerGroupService(session)
        self.settings = get_settings()
    
    def get_latest_peer_stats(
        self,
        peer_key: str,
        horizon: str,
        as_of_date: date | None = None,
    ) -> PeerStats | None:
        """
        Get the latest peer stats for a peer group and horizon.
        
        Args:
            peer_key: Peer group key
            horizon: Return horizon ("ytd", "1y", "3y", "5y")
            as_of_date: Optional as-of date (if None, gets most recent)
            
        Returns:
            PeerStats record or None if not found
        """
        query = (
            select(PeerStats)
            .where(
                and_(
                    PeerStats.peer_key == peer_key,
                    PeerStats.horizon == horizon,
                )
            )
        )
        
        if as_of_date:
            query = query.where(PeerStats.as_of_date <= as_of_date)
        
        query = query.order_by(desc(PeerStats.as_of_date)).limit(1)
        
        result = self.session.execute(query)
        return result.scalar_one_or_none()
    
    def compute_peer_stats(
        self,
        peer_key: str,
        horizon: str,
        as_of_date: date,
    ) -> dict[str, Any]:
        """
        Compute peer stats for a peer group and horizon.
        
        Each share class is counted separately. NULL returns are excluded
        from statistics.
        
        Args:
            peer_key: Peer group key
            horizon: Return horizon ("ytd", "1y", "3y", "5y")
            as_of_date: As-of date for return snapshots
            
        Returns:
            Dictionary with computed stats:
            - peer_key: The peer key
            - horizon: The horizon
            - as_of_date: The as-of date
            - peer_count_total: Total fund/class combinations
            - peer_count_eligible: Fund/class with non-NULL returns
            - peer_median_return: Median return (or None)
            - peer_p25_return: 25th percentile (or None)
            - peer_p75_return: 75th percentile (or None)
            - stats_json: JSON with returns and fund_ids
            - insufficient: Boolean indicating if peer count < hard minimum
        """
        if horizon not in HORIZON_COLUMN_MAP:
            raise ValueError(f"Invalid horizon: {horizon}. Must be one of {list(HORIZON_COLUMN_MAP.keys())}")
        
        return_column = HORIZON_COLUMN_MAP[horizon]
        eligibility_column = HORIZON_ELIGIBILITY_MAP.get(horizon)  # None for YTD
        
        # Get peer group members
        members = self.peer_group_service.get_peer_group_members(peer_key, as_of_date)
        peer_count_total = len(members)
        
        if peer_count_total == 0:
            return self._empty_stats(peer_key, horizon, as_of_date)
        
        # Get latest return snapshots for each member
        returns_data = self._get_latest_snapshots_with_returns(
            members, as_of_date, return_column, eligibility_column
        )
        
        # Filter to eligible fund/class combinations with non-NULL returns
        eligible_returns: list[tuple[str, float]] = []  # (fund_id, return_value)
        
        for fund_id, return_value, is_eligible in returns_data:
            # For YTD, all funds with snapshots are eligible
            # For other horizons, check eligibility flag
            if eligibility_column is None or is_eligible:
                if return_value is not None:
                    eligible_returns.append((fund_id, float(return_value)))
        
        peer_count_eligible = len(eligible_returns)
        
        # Check if peer count is insufficient
        insufficient = peer_count_eligible < self.settings.peer_min_count_hard
        
        # Compute statistics if we have eligible returns
        if peer_count_eligible == 0:
            return {
                "peer_key": peer_key,
                "horizon": horizon,
                "as_of_date": as_of_date,
                "peer_count_total": peer_count_total,
                "peer_count_eligible": 0,
                "peer_median_return": None,
                "peer_p25_return": None,
                "peer_p75_return": None,
                "stats_json": {"returns": [], "fund_ids": []},
                "insufficient": True,
            }
        
        # Sort by return descending (best return first)
        eligible_returns.sort(key=lambda x: x[1], reverse=True)
        
        returns_list = [r[1] for r in eligible_returns]
        fund_ids_list = [r[0] for r in eligible_returns]
        
        # Compute percentiles
        peer_median_return = statistics.median(returns_list)
        peer_p25_return, peer_p75_return = self._compute_percentiles(returns_list)
        
        return {
            "peer_key": peer_key,
            "horizon": horizon,
            "as_of_date": as_of_date,
            "peer_count_total": peer_count_total,
            "peer_count_eligible": peer_count_eligible,
            "peer_median_return": round(peer_median_return, 4),
            "peer_p25_return": round(peer_p25_return, 4) if peer_p25_return else None,
            "peer_p75_return": round(peer_p75_return, 4) if peer_p75_return else None,
            "stats_json": {
                "returns": [round(r, 4) for r in returns_list],
                "fund_ids": fund_ids_list,
            },
            "insufficient": insufficient,
        }
    
    def store_peer_stats(self, stats: dict[str, Any]) -> PeerStats:
        """
        Store computed peer stats in the database.
        
        Uses upsert (insert or update on conflict) to handle re-computation.
        
        Args:
            stats: Dictionary with computed stats (from compute_peer_stats)
            
        Returns:
            PeerStats ORM object
        """
        stmt = insert(PeerStats).values(
            peer_key=stats["peer_key"],
            horizon=stats["horizon"],
            as_of_date=stats["as_of_date"],
            peer_count_total=stats["peer_count_total"],
            peer_count_eligible=stats["peer_count_eligible"],
            peer_median_return=stats.get("peer_median_return"),
            peer_p25_return=stats.get("peer_p25_return"),
            peer_p75_return=stats.get("peer_p75_return"),
            stats_json=stats.get("stats_json"),
        )
        
        # On conflict, update all fields
        # Use index_elements instead of constraint name (more flexible)
        stmt = stmt.on_conflict_do_update(
            index_elements=["peer_key", "horizon", "as_of_date"],
            set_={
                "peer_count_total": stats["peer_count_total"],
                "peer_count_eligible": stats["peer_count_eligible"],
                "peer_median_return": stats.get("peer_median_return"),
                "peer_p25_return": stats.get("peer_p25_return"),
                "peer_p75_return": stats.get("peer_p75_return"),
                "stats_json": stats.get("stats_json"),
                "computed_at": func.now(),
            }
        )
        
        self.session.execute(stmt)
        # Note: commit is handled by caller (computation service) to batch commits
        
        # Fetch the stored/updated record
        return self.get_latest_peer_stats(
            stats["peer_key"],
            stats["horizon"],
            stats["as_of_date"]
        )
    
    def _get_latest_snapshots_with_returns(
        self,
        members: list[Fund],
        as_of_date: date,
        return_column: str,
        eligibility_column: str | None,
    ) -> list[tuple[str, Decimal | None, bool]]:
        """
        Get latest return snapshots for a list of fund/class combinations.
        
        Uses window function to efficiently get latest snapshot per fund/class.
        
        Args:
            members: List of Fund records
            as_of_date: As-of date
            return_column: Name of return column (e.g., "trailing_1y_return")
            eligibility_column: Name of eligibility column (e.g., "eligible_1y") or None
            
        Returns:
            List of tuples: (fund_id, return_value, is_eligible)
            fund_id format: "proj_id|class_abbr_name"
        """
        if not members:
            return []
        
        # Build list of (proj_id, class_abbr_name) tuples
        # Normalize: empty string and "main" are equivalent for return snapshots
        member_keys = [(m.proj_id, m.class_abbr_name if m.class_abbr_name else "") for m in members]
        
        # Use window function to rank snapshots by date per fund/class
        from sqlalchemy import literal_column
        from sqlalchemy.sql import func as sqlfunc
        
        # Build conditions for all fund/class combinations
        # If class_abbr_name is empty, also try "main" and "Main" (common in return snapshots)
        conditions = []
        for proj_id, class_abbr_name in member_keys:
            if not class_abbr_name:
                # Empty class: try "", "main", and "Main"
                conditions.append(
                    and_(
                        FundReturnSnapshot.proj_id == proj_id,
                        or_(
                            FundReturnSnapshot.class_abbr_name == "",
                            FundReturnSnapshot.class_abbr_name == "main",
                            FundReturnSnapshot.class_abbr_name == "Main"
                        )
                    )
                )
            else:
                conditions.append(
                    and_(
                        FundReturnSnapshot.proj_id == proj_id,
                        FundReturnSnapshot.class_abbr_name == class_abbr_name
                    )
                )
        
        from sqlalchemy import or_
        
        # Subquery with row number to get latest snapshot per fund/class
        row_number = sqlfunc.row_number().over(
            partition_by=[FundReturnSnapshot.proj_id, FundReturnSnapshot.class_abbr_name],
            order_by=desc(FundReturnSnapshot.as_of_date)
        ).label("row_num")
        
        subquery = (
            select(
                FundReturnSnapshot.proj_id,
                FundReturnSnapshot.class_abbr_name,
                getattr(FundReturnSnapshot, return_column).label("return_value"),
                (
                    getattr(FundReturnSnapshot, eligibility_column).label("is_eligible")
                    if eligibility_column
                    else literal_column("true").label("is_eligible")
                ),
                row_number,
            )
            .where(
                and_(
                    or_(*conditions),
                    FundReturnSnapshot.as_of_date <= as_of_date,
                )
            )
            .subquery()
        )
        
        # Select only the latest snapshot (row_num = 1)
        query = (
            select(
                subquery.c.proj_id,
                subquery.c.class_abbr_name,
                subquery.c.return_value,
                subquery.c.is_eligible,
            )
            .where(subquery.c.row_num == 1)
        )
        
        result = self.session.execute(query)
        
        returns_data = []
        for row in result.fetchall():
            # Normalize class_abbr_name: "main" or "Main" -> "" for consistency
            normalized_class = "" if row.class_abbr_name in ("main", "Main") else row.class_abbr_name
            fund_id = f"{row.proj_id}|{normalized_class}"
            returns_data.append((fund_id, row.return_value, row.is_eligible))
        
        return returns_data
    
    def _compute_percentiles(
        self,
        returns_list: list[float],
    ) -> tuple[float | None, float | None]:
        """
        Compute 25th and 75th percentiles of returns.
        
        Args:
            returns_list: List of return values (sorted descending)
            
        Returns:
            Tuple of (p25, p75) or (None, None) if insufficient data
        """
        if len(returns_list) < 4:
            return None, None
        
        try:
            # Use statistics.quantiles for Python 3.8+
            quantiles = statistics.quantiles(returns_list, n=4)
            return quantiles[0], quantiles[2]  # Q1 (25th) and Q3 (75th)
        except statistics.StatisticsError:
            return None, None
    
    def _empty_stats(
        self,
        peer_key: str,
        horizon: str,
        as_of_date: date,
    ) -> dict[str, Any]:
        """Return empty stats for a peer group with no members."""
        return {
            "peer_key": peer_key,
            "horizon": horizon,
            "as_of_date": as_of_date,
            "peer_count_total": 0,
            "peer_count_eligible": 0,
            "peer_median_return": None,
            "peer_p25_return": None,
            "peer_p75_return": None,
            "stats_json": {"returns": [], "fund_ids": []},
            "insufficient": True,
        }
