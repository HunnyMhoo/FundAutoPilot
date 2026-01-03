"""
Compare Service

Aggregates fund comparison data from database and SEC API for side-by-side comparison.
"""

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import select, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fund_orm import Fund, AMC, FundReturnSnapshot
from app.models.fund import (
    CompareFundData,
    CompareFundsResponse,
    FundIdentity,
    RiskData,
    FeeGroup,
    FeeRow,
    DealingConstraints,
    DistributionData,
    DividendDetail,
    MissingFlags,
    ReturnsData,
    PeerMetricsResponse,
)
from app.utils.sec_api_client import SECAPIClient, SECAPIErrorType
from app.utils.fee_grouping import group_fees, get_category_display_label, FeeGroupCategory
from app.core.database import SyncSessionLocal
from app.services.peer_ranking_service import PeerRankingService

logger = logging.getLogger(__name__)


def select_default_class(fund_abbr: str | None, class_list: list[dict[str, Any]]) -> str | None:
    """
    Select default class for a fund using deterministic rules.
    
    Priority:
    1. Match fund_abbr to class_abbr_name (exact match)
    2. Prefer class_abbr_name that is None, "-", or "main" (fund-level)
    3. Otherwise, take first alphabetically by class_abbr_name
    
    Args:
        fund_abbr: Fund abbreviation to match
        class_list: List of dicts with class_abbr_name field
        
    Returns:
        Selected class_abbr_name string, or None if no classes available
    """
    if not class_list:
        return None
    
    # Priority 1: Exact match with fund_abbr
    if fund_abbr:
        for item in class_list:
            class_abbr = item.get("class_abbr_name")
            if class_abbr and class_abbr.lower() == fund_abbr.lower():
                return class_abbr
    
    # Priority 2: Fund-level classes (None, "-", "main")
    fund_level_classes = [None, "-", "main"]
    for item in class_list:
        class_abbr = item.get("class_abbr_name")
        if class_abbr in fund_level_classes or (class_abbr and class_abbr.lower() == "main"):
            return class_abbr
    
    # Priority 3: First alphabetically
    sorted_classes = sorted(
        [item for item in class_list if item.get("class_abbr_name")],
        key=lambda x: x.get("class_abbr_name", "")
    )
    if sorted_classes:
        return sorted_classes[0].get("class_abbr_name")
    
    # Fallback: first item's class_abbr_name
    if class_list:
        return class_list[0].get("class_abbr_name")
    
    return None


def filter_by_class(items: list[dict[str, Any]], selected_class: str | None) -> list[dict[str, Any]]:
    """
    Filter items by selected class.
    
    Args:
        items: List of items with class_abbr_name field
        selected_class: Class abbreviation to filter by (None means fund-level)
        
    Returns:
        Filtered list of items matching the class
    """
    if not selected_class:
        # Return fund-level items (None, "-", "main")
        return [
            item for item in items
            if not item.get("class_abbr_name") 
            or item.get("class_abbr_name") in ["-", "main"]
            or item.get("class_abbr_name", "").lower() == "main"
        ]
    
    return [
        item for item in items
        if item.get("class_abbr_name") == selected_class
    ]


class CompareService:
    """Service for comparing funds."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_client = SECAPIClient()
    
    async def compare_funds(self, fund_ids: list[str]) -> CompareFundsResponse:
        """
        Compare multiple funds side-by-side.
        
        Args:
            fund_ids: List of fund IDs (2-3 funds max, validated by endpoint)
            
        Returns:
            CompareFundsResponse with comparison data for each fund
        """
        errors = []
        compare_data_list = []
        
        # Process each fund in parallel where possible
        for fund_id in fund_ids:
            try:
                fund_data = await self._fetch_fund_comparison_data(fund_id)
                compare_data_list.append(fund_data)
            except Exception as e:
                error_msg = f"Failed to fetch comparison data for {fund_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                # Create a minimal fund data entry with missing flags
                compare_data_list.append(
                    CompareFundData(
                        fund_id=fund_id,
                        identity=FundIdentity(
                            fund_id=fund_id,
                            fund_name="Unknown",
                            fund_abbr=None,
                            amc_id="",
                            amc_name="Unknown",
                            category=None,
                        ),
                        risk=None,
                        fees=[],
                        dealing_constraints=None,
                        distribution=None,
                        returns=None,
                        peer_metrics=None,
                        missing_flags=MissingFlags(
                            fees_missing=True,
                            risk_missing=True,
                            dealing_missing=True,
                            distribution_missing=True,
                        ),
                        data_freshness={},
                    )
                )
        
        # Compute peer metrics for all funds with consistent as-of date
        await self._compute_peer_metrics(compare_data_list)
        
        return CompareFundsResponse(
            funds=compare_data_list,
            errors=errors,
        )
    
    async def _compute_peer_metrics(self, compare_data_list: list[CompareFundData]) -> None:
        """
        Compute peer metrics for all funds in compare data list.
        
        Uses a consistent as-of date across all funds (latest common date).
        Optimized to use batch computation per horizon for efficiency.
        
        Args:
            compare_data_list: List of CompareFundData objects to update with peer metrics
        """
        # Determine common as-of date from return data
        as_of_dates = []
        for fund_data in compare_data_list:
            if fund_data.returns and fund_data.returns.as_of_date:
                try:
                    as_of_date = date.fromisoformat(fund_data.returns.as_of_date)
                    as_of_dates.append(as_of_date)
                except (ValueError, AttributeError):
                    pass
        
        if not as_of_dates:
            # No return data available, skip peer metrics
            logger.warning("No return data available for peer metrics computation")
            return
        
        # Use latest common date (or latest available if no common date)
        common_as_of_date = max(as_of_dates)
        
        # Horizons to compute (1Y and 3Y required, YTD and 5Y optional)
        horizons = ["1y", "3y", "ytd", "5y"]
        
        # Collect fund identifiers first (with mapping to fund_data)
        fund_identifier_map: dict[str, CompareFundData] = {}
        
        # Use sync session for PeerRankingService
        with SyncSessionLocal() as sync_session:
            ranking_service = PeerRankingService(sync_session)
            
            # First pass: collect all fund identifiers
            for fund_data in compare_data_list:
                if not fund_data.returns or not fund_data.returns.as_of_date:
                    continue
                
                try:
                    # Get selected class from dealing_constraints or distribution
                    selected_class = None
                    if fund_data.dealing_constraints and fund_data.dealing_constraints.class_shown:
                        selected_class = fund_data.dealing_constraints.class_shown
                    elif fund_data.distribution and fund_data.distribution.class_shown:
                        selected_class = fund_data.distribution.class_shown
                    
                    # Look up the actual fund record to get the correct class_abbr_name
                    sync_fund_query = select(Fund).where(Fund.proj_id == fund_data.fund_id)
                    if selected_class:
                        sync_fund_query = sync_fund_query.where(Fund.class_abbr_name == selected_class)
                    else:
                        # Default to fund-level (empty class)
                        sync_fund_query = sync_fund_query.where(Fund.class_abbr_name == "")
                    
                    sync_result = sync_session.execute(sync_fund_query)
                    fund_record = sync_result.scalar_one_or_none()
                    
                    if not fund_record:
                        logger.warning(f"Fund not found for peer metrics: {fund_data.fund_id} (class: {selected_class})")
                        continue
                    
                    # Use class_abbr_name as identifier if it exists, otherwise use proj_id
                    fund_identifier = fund_record.class_abbr_name if fund_record.class_abbr_name else fund_record.proj_id
                    fund_identifier_map[fund_identifier] = fund_data
                    
                except Exception as e:
                    logger.warning(f"Failed to get fund identifier for {fund_data.fund_id}: {e}")
                    continue
            
            # Second pass: compute ranks per horizon in batch
            for horizon in horizons:
                try:
                    fund_identifiers = list(fund_identifier_map.keys())
                    if not fund_identifiers:
                        continue
                    
                    # Compute ranks for all funds in this horizon
                    rank_results = ranking_service.compute_peer_ranks_batch(
                        fund_identifiers,
                        horizon,
                        common_as_of_date,
                    )
                    
                    # Map results back to fund_data
                    for fund_identifier, rank_result in rank_results.items():
                        if fund_identifier in fund_identifier_map:
                            fund_data = fund_identifier_map[fund_identifier]
                            
                            # Initialize peer_metrics dict if needed
                            if fund_data.peer_metrics is None:
                                fund_data.peer_metrics = {}
                            
                            # Add this horizon's metrics
                            fund_data.peer_metrics[horizon] = PeerMetricsResponse.from_peer_rank_result(rank_result)
                            
                except Exception as e:
                    logger.warning(f"Failed to compute peer ranks for horizon {horizon}: {e}")
                    continue
    
    async def _fetch_fund_comparison_data(self, fund_id: str) -> CompareFundData:
        """
        Fetch comparison data for a single fund.
        
        Args:
            fund_id: Fund ID (proj_id)
            
        Returns:
            CompareFundData object
        """
        # 1. Fetch identity and risk from database
        # Handle funds with multiple share classes by preferring fund-level records (empty class_abbr_name)
        query = (
            select(Fund)
            .join(AMC, Fund.amc_id == AMC.unique_id)
            .options(selectinload(Fund.amc))
            .where(Fund.proj_id == fund_id)
            .order_by(
                # Prefer fund-level records (empty class_abbr_name) first
                case((Fund.class_abbr_name == "", 0), else_=1).asc(),
                Fund.class_abbr_name.asc()
            )
            .limit(1)
        )
        result = await self.db.execute(query)
        fund = result.scalar_one_or_none()
        
        if fund is None:
            raise ValueError(f"Fund not found: {fund_id}")
        
        # Get AMC name
        amc_name = "Unknown"
        if fund.amc:
            amc_name = fund.amc.name_en
        else:
            amc_res = await self.db.execute(select(AMC).where(AMC.unique_id == fund.amc_id))
            amc_obj = amc_res.scalar_one_or_none()
            if amc_obj:
                amc_name = amc_obj.name_en
        
        # Build identity
        identity = FundIdentity(
            fund_id=fund.proj_id,
            fund_name=fund.fund_name_en,
            fund_abbr=fund.fund_abbr,
            amc_id=fund.amc_id,
            amc_name=amc_name,
            category=fund.category,
        )
        
        # 2. Build risk data from database
        risk = None
        risk_missing = True
        if fund.risk_level_int is not None or fund.risk_level is not None:
            risk = RiskData(
                risk_level=str(fund.risk_level_int) if fund.risk_level_int is not None else fund.risk_level,
                risk_level_desc=fund.risk_level_desc,
                last_upd_date=fund.risk_last_upd_date.isoformat() if fund.risk_last_upd_date else None,
            )
            risk_missing = False
        
        # 3. Process fees from cached DB data (fee_data_raw)
        fees_groups = []
        fees_missing = True
        selected_class = None
        
        if fund.fee_data_raw:
            try:
                # fee_data_raw is a list of fee rows
                fee_rows = fund.fee_data_raw if isinstance(fund.fee_data_raw, list) else []
                
                if fee_rows:
                    # Determine selected class from fee rows
                    unique_classes = list(set(
                        row.get("class_abbr_name") for row in fee_rows if row.get("class_abbr_name")
                    ))
                    selected_class = select_default_class(fund.fund_abbr, [{"class_abbr_name": c} for c in unique_classes])
                    
                    # Filter fees by selected class
                    filtered_fees = filter_by_class(fee_rows, selected_class)
                    
                    # Group fees
                    grouped = group_fees(filtered_fees)
                    
                    # Convert to FeeGroup models
                    for category, fee_list in grouped.items():
                        fee_rows_models = [
                            FeeRow(
                                fee_type_desc=row.get("fee_type_desc", ""),
                                rate=row.get("rate"),
                                rate_unit=row.get("rate_unit"),
                                actual_value=row.get("actual_value"),
                                actual_value_unit=row.get("actual_value_unit"),
                                fee_other_desc=row.get("fee_other_desc"),
                                last_upd_date=row.get("last_upd_date"),
                                class_abbr_name=row.get("class_abbr_name"),
                            )
                            for row in fee_list
                        ]
                        fees_groups.append(
                            FeeGroup(
                                category=category,
                                display_label=get_category_display_label(category),
                                fees=fee_rows_models,
                            )
                        )
                    fees_missing = False
            except Exception as e:
                logger.warning(f"Failed to process fee_data_raw for {fund_id}: {e}")
        
        # 4. Fetch dealing constraints from SEC API
        dealing_constraints = None
        dealing_missing = True
        filtered_investment = None  # Initialize here so it's available for data_freshness
        
        redemption_data, redemption_error = self.api_client.fetch_redemption(fund_id)
        investment_data, investment_error = self.api_client.fetch_investment(fund_id)
        
        if redemption_error is None or investment_error is None:
            # At least one succeeded
            dealing_missing = False
            
            # Filter investment data by selected class (if we have one from fees, reuse it)
            if investment_data and selected_class is not None:
                filtered_investment_list = filter_by_class(investment_data, selected_class)
                filtered_investment = filtered_investment_list[0] if filtered_investment_list else None
            elif investment_data:
                # No class selection yet, use first item (or try to select)
                if len(investment_data) > 1:
                    selected_class = select_default_class(fund.fund_abbr, investment_data)
                    filtered_investment_list = filter_by_class(investment_data, selected_class)
                    filtered_investment = filtered_investment_list[0] if filtered_investment_list else investment_data[0]
                else:
                    filtered_investment = investment_data[0] if investment_data else None
            
            dealing_constraints = DealingConstraints(
                redemp_period=redemption_data.get("redemp_period") if redemption_data else None,
                redemp_period_oth=redemption_data.get("redemp_period_oth") if redemption_data else None,
                settlement_period=redemption_data.get("settlement_period") if redemption_data else None,
                buying_cut_off_time=redemption_data.get("buying_cut_off_time") if redemption_data else None,
                selling_cut_off_time=redemption_data.get("selling_cut_off_time") if redemption_data else None,
                minimum_sub_ipo=filtered_investment.get("minimum_sub_ipo") if filtered_investment else None,
                minimum_sub_ipo_cur=filtered_investment.get("minimum_sub_ipo_cur") if filtered_investment else None,
                minimum_sub=filtered_investment.get("minimum_sub") if filtered_investment else None,
                minimum_sub_cur=filtered_investment.get("minimum_sub_cur") if filtered_investment else None,
                minimum_redempt=filtered_investment.get("minimum_redempt") if filtered_investment else None,
                minimum_redempt_cur=filtered_investment.get("minimum_redempt_cur") if filtered_investment else None,
                minimum_redempt_unit=filtered_investment.get("minimum_redempt_unit") if filtered_investment else None,
                lowbal_val=float(filtered_investment.get("lowbal_val")) if filtered_investment and filtered_investment.get("lowbal_val") not in (None, "") else None,
                lowbal_val_cur=filtered_investment.get("lowbal_val_cur") if filtered_investment else None,
                lowbal_unit=float(filtered_investment.get("lowbal_unit")) if filtered_investment and filtered_investment.get("lowbal_unit") not in (None, "") else None,
                last_upd_date_redemption=redemption_data.get("last_upd_date") if redemption_data else None,
                last_upd_date_investment=filtered_investment.get("last_upd_date") if filtered_investment else None,
                class_shown=selected_class,
            )
        
        # 5. Fetch distribution from SEC API
        distribution = None
        distribution_missing = True
        filtered_dividend = None  # Initialize here so it's available for data_freshness
        
        dividend_data, dividend_error = self.api_client.fetch_dividend(fund_id)
        
        if dividend_error is None and dividend_data:
            distribution_missing = False
            
            # Filter by selected class (reuse from fees if available)
            if selected_class is not None:
                filtered_dividend_list = filter_by_class(dividend_data, selected_class)
                filtered_dividend = filtered_dividend_list[0] if filtered_dividend_list else None
            else:
                if len(dividend_data) > 1:
                    selected_class = select_default_class(fund.fund_abbr, dividend_data)
                    filtered_dividend_list = filter_by_class(dividend_data, selected_class)
                    filtered_dividend = filtered_dividend_list[0] if filtered_dividend_list else dividend_data[0]
                else:
                    filtered_dividend = dividend_data[0] if dividend_data else None
            
            if filtered_dividend:
                # Get most recent dividend from dividend_details array (if available)
                recent_dividends = []
                dividend_details = filtered_dividend.get("dividend_details", [])
                if dividend_details:
                    # Sort by payment_date descending, take up to 3 most recent
                    sorted_details = sorted(
                        dividend_details,
                        key=lambda x: x.get("payment_date", "") or "",
                        reverse=True
                    )[:3]
                    
                    recent_dividends = [
                        DividendDetail(
                            book_closing_date=detail.get("book_closing_date"),
                            payment_date=detail.get("payment_date"),
                            dividend_per_share=detail.get("dividend_per_share"),
                        )
                        for detail in sorted_details
                    ]
                
                distribution = DistributionData(
                    dividend_policy=filtered_dividend.get("dividend_policy"),
                    dividend_policy_remark=filtered_dividend.get("dividend_policy_remark"),
                    recent_dividends=recent_dividends,
                    last_upd_date=filtered_dividend.get("last_upd_date"),
                    class_shown=selected_class,
                )
        
        # 6. Fetch return data from FundReturnSnapshot
        returns_data = await self._fetch_return_data(fund.proj_id, selected_class)
        
        # 7. Compute peer metrics (will be done after all funds are fetched to determine common as-of date)
        # This will be handled in compare_funds() method
        
        # Build data freshness dict
        data_freshness = {
            "risk": fund.risk_last_upd_date.isoformat() if fund.risk_last_upd_date else None,
            "fees": fund.fee_data_last_upd_date.isoformat() if fund.fee_data_last_upd_date else None,
            "dealing_redemption": redemption_data.get("last_upd_date") if redemption_data else None,
            "dealing_investment": filtered_investment.get("last_upd_date") if filtered_investment else None,
            "distribution": filtered_dividend.get("last_upd_date") if filtered_dividend else None,
        }
        
        return CompareFundData(
            fund_id=fund.proj_id,
            identity=identity,
            risk=risk,
            fees=fees_groups,
            dealing_constraints=dealing_constraints,
            distribution=distribution,
            returns=returns_data,
            missing_flags=MissingFlags(
                fees_missing=fees_missing,
                risk_missing=risk_missing,
                dealing_missing=dealing_missing,
                distribution_missing=distribution_missing,
            ),
            data_freshness=data_freshness,
        )
    
    async def _fetch_return_data(
        self,
        proj_id: str,
        class_abbr_name: str | None,
    ) -> ReturnsData | None:
        """
        Fetch return data from FundReturnSnapshot for a fund/class.
        
        Args:
            proj_id: Fund project ID
            class_abbr_name: Class abbreviation (None means fund-level)
            
        Returns:
            ReturnsData object or None if no data available
        """
        class_name = class_abbr_name if class_abbr_name else ""
        
        # Get latest snapshot
        query = (
            select(FundReturnSnapshot)
            .where(
                FundReturnSnapshot.proj_id == proj_id,
                FundReturnSnapshot.class_abbr_name == class_name,
            )
            .order_by(desc(FundReturnSnapshot.as_of_date))
            .limit(1)
        )
        
        result = await self.db.execute(query)
        snapshot = result.scalar_one_or_none()
        
        if snapshot is None:
            return None
        
        return ReturnsData(
            ytd=float(snapshot.ytd_return) if snapshot.ytd_return is not None else None,
            trailing_1y=float(snapshot.trailing_1y_return) if snapshot.trailing_1y_return is not None else None,
            trailing_3y=float(snapshot.trailing_3y_return) if snapshot.trailing_3y_return is not None else None,
            trailing_5y=float(snapshot.trailing_5y_return) if snapshot.trailing_5y_return is not None else None,
            as_of_date=snapshot.as_of_date.isoformat() if snapshot.as_of_date else None,
        )

