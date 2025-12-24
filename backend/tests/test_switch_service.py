"""Unit tests for SwitchService."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.switch_service import SwitchService
from app.models.fund import SwitchPreviewRequest
from app.models.fund_orm import Fund


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def switch_service(mock_db):
    """Create SwitchService instance with mocked database."""
    return SwitchService(mock_db)


class TestSwitchServiceFeeDelta:
    """Tests for fee delta calculation."""
    
    @pytest.mark.asyncio
    async def test_fee_delta_positive(self, switch_service, mock_db):
        """Test positive fee delta (target ER > current ER)."""
        # Mock funds
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Equity"
        
        # Mock database queries
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        async def execute_side_effect(query):
            # First call for current fund, second for target
            if not hasattr(execute_side_effect, 'call_count'):
                execute_side_effect.call_count = 0
            execute_side_effect.call_count += 1
            if execute_side_effect.call_count == 1:
                return mock_result_current
            else:
                return mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        # Verify fee delta
        assert result.deltas.expense_ratio_delta == 0.5  # 2.0 - 1.5
        assert result.deltas.annual_fee_thb_delta == 500  # 100000 * 0.5 / 100
        assert result.coverage.status == "HIGH"
    
    @pytest.mark.asyncio
    async def test_fee_delta_negative(self, switch_service, mock_db):
        """Test negative fee delta (target ER < current ER)."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("2.5")
        current_fund.risk_level_int = 5
        current_fund.risk_level = "5"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("1.0")
        target_fund.risk_level_int = 4
        target_fund.risk_level = "4"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        # Verify negative delta
        assert result.deltas.expense_ratio_delta == -1.5  # 1.0 - 2.5
        assert result.deltas.annual_fee_thb_delta == -1500  # 100000 * -1.5 / 100
        assert result.coverage.status == "HIGH"
    
    @pytest.mark.asyncio
    async def test_fee_delta_zero(self, switch_service, mock_db):
        """Test zero fee delta (same ER)."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("1.5")
        target_fund.risk_level_int = 4
        target_fund.risk_level = "4"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.deltas.expense_ratio_delta == 0.0
        assert result.deltas.annual_fee_thb_delta == 0
        assert result.coverage.status == "HIGH"
    
    @pytest.mark.asyncio
    async def test_fee_delta_missing_current_er(self, switch_service, mock_db):
        """Test BLOCKED when current fund missing expense ratio."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = None
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.coverage.status == "BLOCKED"
        assert "current_expense_ratio" in result.coverage.missing_fields
        assert result.coverage.blocking_reason is not None
        assert result.coverage.suggested_next_action is not None
        assert result.deltas.expense_ratio_delta is None
        assert result.deltas.annual_fee_thb_delta is None
    
    @pytest.mark.asyncio
    async def test_fee_delta_missing_target_er(self, switch_service, mock_db):
        """Test BLOCKED when target fund missing expense ratio."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = None
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.coverage.status == "BLOCKED"
        assert "target_expense_ratio" in result.coverage.missing_fields


class TestSwitchServiceRiskDelta:
    """Tests for risk level delta calculation."""
    
    @pytest.mark.asyncio
    async def test_risk_delta_positive(self, switch_service, mock_db):
        """Test positive risk delta (target > current)."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.deltas.risk_level_delta == 2  # 6 - 4
        assert result.coverage.status == "HIGH"
    
    @pytest.mark.asyncio
    async def test_risk_delta_missing(self, switch_service, mock_db):
        """Test MEDIUM coverage when risk missing."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = None
        current_fund.risk_level = None
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.deltas.risk_level_delta is None
        assert result.coverage.status == "MEDIUM"
        assert "current_risk_level" in result.coverage.missing_fields


class TestSwitchServiceCategoryChange:
    """Tests for category change detection."""
    
    @pytest.mark.asyncio
    async def test_category_changed(self, switch_service, mock_db):
        """Test category change detection."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 4
        target_fund.risk_level = "4"
        target_fund.category = "Fixed Income"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.deltas.category_changed is True
        assert result.coverage.status == "HIGH"
    
    @pytest.mark.asyncio
    async def test_category_not_changed(self, switch_service, mock_db):
        """Test category unchanged detection."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.deltas.category_changed is False


class TestSwitchServiceCoverage:
    """Tests for coverage classification."""
    
    @pytest.mark.asyncio
    async def test_coverage_high(self, switch_service, mock_db):
        """Test HIGH coverage (all data present)."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Equity"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.coverage.status == "HIGH"
        assert len(result.coverage.missing_fields) == 0
    
    @pytest.mark.asyncio
    async def test_coverage_low(self, switch_service, mock_db):
        """Test LOW coverage (fee present, risk and category missing)."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = None
        current_fund.risk_level = None
        current_fund.category = None
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = None
        target_fund.risk_level = None
        target_fund.category = None
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        assert result.coverage.status == "LOW"
        assert "current_risk_level" in result.coverage.missing_fields
        assert "target_risk_level" in result.coverage.missing_fields
        assert "current_category" in result.coverage.missing_fields
        assert "target_category" in result.coverage.missing_fields


class TestSwitchServiceValidation:
    """Tests for input validation."""
    
    @pytest.mark.asyncio
    async def test_same_fund_error(self, switch_service, mock_db):
        """Test error when current and target are the same."""
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND1",
            amount_thb=100000.0
        )
        
        with pytest.raises(ValueError, match="must be different"):
            await switch_service.get_switch_preview(request)
    
    @pytest.mark.asyncio
    async def test_fund_not_found(self, switch_service, mock_db):
        """Test error when fund not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        request = SwitchPreviewRequest(
            current_fund_id="NONEXISTENT",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        with pytest.raises(ValueError, match="not found"):
            await switch_service.get_switch_preview(request)


class TestSwitchServiceExplanation:
    """Tests for explanation generation."""
    
    @pytest.mark.asyncio
    async def test_explanation_includes_all_sections(self, switch_service, mock_db):
        """Test that explanation includes fee, risk, and category sections."""
        current_fund = MagicMock(spec=Fund)
        current_fund.proj_id = "FUND1"
        current_fund.fund_name_en = "Current Fund"
        current_fund.expense_ratio = Decimal("1.5")
        current_fund.risk_level_int = 4
        current_fund.risk_level = "4"
        current_fund.category = "Equity"
        
        target_fund = MagicMock(spec=Fund)
        target_fund.proj_id = "FUND2"
        target_fund.fund_name_en = "Target Fund"
        target_fund.expense_ratio = Decimal("2.0")
        target_fund.risk_level_int = 6
        target_fund.risk_level = "6"
        target_fund.category = "Fixed Income"
        
        mock_result_current = MagicMock()
        mock_result_current.scalar_one_or_none.return_value = current_fund
        mock_result_target = MagicMock()
        mock_result_target.scalar_one_or_none.return_value = target_fund
        
        call_count = [0]
        async def execute_side_effect(query):
            call_count[0] += 1
            return mock_result_current if call_count[0] == 1 else mock_result_target
        
        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        
        request = SwitchPreviewRequest(
            current_fund_id="FUND1",
            target_fund_id="FUND2",
            amount_thb=100000.0
        )
        
        result = await switch_service.get_switch_preview(request)
        
        # Verify explanation structure
        assert result.explainability.rationale_short
        assert result.explainability.rationale_paragraph
        assert result.explainability.formula_display
        assert len(result.explainability.assumptions) > 0
        assert len(result.explainability.disclaimers) > 0
        
        # Verify explanation mentions key elements
        assert "Current Fund" in result.explainability.rationale_paragraph
        assert "Target Fund" in result.explainability.rationale_paragraph
        assert "100,000" in result.explainability.rationale_paragraph or "100000" in result.explainability.rationale_paragraph

