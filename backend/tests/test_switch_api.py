"""Integration tests for Switch API endpoint."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from main import app
from app.models.fund import SwitchPreviewResponse


@pytest_asyncio.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_switch_service():
    """Create a mock switch service."""
    with patch('app.api.switch.SwitchService') as mock:
        yield mock


class TestSwitchPreviewAPI:
    """Tests for POST /switch/preview endpoint."""
    
    @pytest.mark.asyncio
    async def test_switch_preview_success(self, client, mock_switch_service):
        """Test successful switch preview generation."""
        from app.models.fund import (
            SwitchPreviewResponse,
            InputsEcho,
            Deltas,
            Explainability,
            Coverage,
        )
        
        mock_response = SwitchPreviewResponse(
            inputs_echo=InputsEcho(
                current_fund_id="FUND1",
                target_fund_id="FUND2",
                amount_thb=100000.0,
                current_expense_ratio=1.5,
                target_expense_ratio=2.0,
                current_risk_level="4",
                target_risk_level="6",
                current_category="Equity",
                target_category="Equity",
            ),
            deltas=Deltas(
                expense_ratio_delta=0.5,
                annual_fee_thb_delta=500,
                risk_level_delta=2,
                category_changed=False,
            ),
            explainability=Explainability(
                rationale_short="Increases annual fee drag by approximately 500 THB per year. Risk level increases from 4 to 6.",
                rationale_paragraph="Switching from Current Fund to Target Fund increases expected fee drag by approximately 500 THB per year on an investment of 100,000 THB. This calculation uses expense ratios of 1.50% (current) and 2.00% (target). Risk level moves from 4 to 6, indicating higher risk exposure. Category remains Equity, maintaining similar diversification characteristics. This is an illustrative estimate based on disclosed expense ratios and metadata, not a forecast of future performance.",
                formula_display="Annual fee difference = Amount × (Target expense ratio − Current expense ratio)",
                assumptions=[
                    "Expense ratios remain constant (actual ratios may change over time).",
                    "Calculation uses annual expense ratio only (excludes one-time fees).",
                    "No market performance or tax implications are considered.",
                ],
                disclaimers=[
                    "Illustrative estimate for education only. Not financial advice.",
                    "Expense ratio may change over time. Check latest factsheet.",
                ],
            ),
            coverage=Coverage(
                status="HIGH",
                missing_fields=[],
                blocking_reason=None,
                suggested_next_action=None,
            ),
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_switch_preview = AsyncMock(return_value=mock_response)
        mock_switch_service.return_value = mock_service_instance
        
        request_data = {
            "current_fund_id": "FUND1",
            "target_fund_id": "FUND2",
            "amount_thb": 100000.0
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["coverage"]["status"] == "HIGH"
        assert data["deltas"]["expense_ratio_delta"] == 0.5
        assert data["deltas"]["annual_fee_thb_delta"] == 500
        assert data["deltas"]["risk_level_delta"] == 2
        assert data["deltas"]["category_changed"] is False
    
    @pytest.mark.asyncio
    async def test_switch_preview_blocked(self, client, mock_switch_service):
        """Test BLOCKED coverage when expense ratio missing."""
        from app.models.fund import (
            SwitchPreviewResponse,
            InputsEcho,
            Deltas,
            Explainability,
            Coverage,
        )
        
        mock_response = SwitchPreviewResponse(
            inputs_echo=InputsEcho(
                current_fund_id="FUND1",
                target_fund_id="FUND2",
                amount_thb=100000.0,
                current_expense_ratio=None,
                target_expense_ratio=2.0,
                current_risk_level=None,
                target_risk_level="6",
                current_category=None,
                target_category="Equity",
            ),
            deltas=Deltas(
                expense_ratio_delta=None,
                annual_fee_thb_delta=None,
                risk_level_delta=None,
                category_changed=None,
            ),
            explainability=Explainability(
                rationale_short="Fee impact cannot be calculated due to missing expense ratio data.",
                rationale_paragraph="Fee impact cannot be calculated for switching from Current Fund to Target Fund due to missing expense ratio data.",
                formula_display="Annual fee difference = Amount × (Target expense ratio − Current expense ratio)",
                assumptions=[],
                disclaimers=[],
            ),
            coverage=Coverage(
                status="BLOCKED",
                missing_fields=["current_expense_ratio"],
                blocking_reason="Expense ratio data is required for fee impact calculation.",
                suggested_next_action="Choose another fund with fee data.",
            ),
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_switch_preview = AsyncMock(return_value=mock_response)
        mock_switch_service.return_value = mock_service_instance
        
        request_data = {
            "current_fund_id": "FUND1",
            "target_fund_id": "FUND2",
            "amount_thb": 100000.0
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["coverage"]["status"] == "BLOCKED"
        assert "current_expense_ratio" in data["coverage"]["missing_fields"]
        assert data["coverage"]["blocking_reason"] is not None
        assert data["coverage"]["suggested_next_action"] is not None
    
    @pytest.mark.asyncio
    async def test_switch_preview_same_fund(self, client, mock_switch_service):
        """Test 400 error when current and target are the same."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_switch_preview = AsyncMock(
            side_effect=ValueError("Current and target funds must be different")
        )
        mock_switch_service.return_value = mock_service_instance
        
        request_data = {
            "current_fund_id": "FUND1",
            "target_fund_id": "FUND1",
            "amount_thb": 100000.0
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "must be different" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_switch_preview_fund_not_found(self, client, mock_switch_service):
        """Test 404 error when fund not found."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_switch_preview = AsyncMock(
            side_effect=ValueError("Fund not found: NONEXISTENT")
        )
        mock_switch_service.return_value = mock_service_instance
        
        request_data = {
            "current_fund_id": "NONEXISTENT",
            "target_fund_id": "FUND2",
            "amount_thb": 100000.0
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_switch_preview_invalid_amount_too_low(self, client):
        """Test 422 validation error when amount is too low."""
        request_data = {
            "current_fund_id": "FUND1",
            "target_fund_id": "FUND2",
            "amount_thb": 500.0  # Below minimum of 1000
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_switch_preview_invalid_amount_too_high(self, client):
        """Test 422 validation error when amount is too high."""
        request_data = {
            "current_fund_id": "FUND1",
            "target_fund_id": "FUND2",
            "amount_thb": 2000000000.0  # Above maximum of 1,000,000,000
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_switch_preview_missing_fields(self, client):
        """Test 422 validation error when required fields are missing."""
        request_data = {
            "current_fund_id": "FUND1",
            # Missing target_fund_id and amount_thb
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_switch_preview_unexpected_error(self, client, mock_switch_service):
        """Test 500 error handling for unexpected exceptions."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_switch_preview = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_switch_service.return_value = mock_service_instance
        
        request_data = {
            "current_fund_id": "FUND1",
            "target_fund_id": "FUND2",
            "amount_thb": 100000.0
        }
        
        response = await client.post("/switch/preview", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "unexpected error" in data["detail"].lower()

