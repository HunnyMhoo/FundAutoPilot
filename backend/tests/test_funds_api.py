"""Tests for Fund API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from main import app
from app.models.fund import FundSummary, FundListResponse


@pytest.fixture
def mock_fund_service():
    """Create a mock fund service."""
    with patch('app.api.funds.FundService') as mock:
        yield mock


import pytest_asyncio

@pytest_asyncio.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestListFunds:
    """Tests for GET /funds endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_funds_success(self, client, mock_fund_service):
        """Test successful fund listing."""
        # Mock response
        mock_response = FundListResponse(
            items=[
                FundSummary(
                    fund_id="M0001_2024",
                    fund_name="Test Fund A",
                    amc_name="Test AMC",
                    category="Equity",
                    risk_level="5",
                    expense_ratio=1.5,
                ),
            ],
            next_cursor="eyJuIjoiVGVzdCBGdW5kIEIiLCJpIjoiTTAwMDJfMjAyNCJ9",
            as_of_date="2024-12-23",
            data_snapshot_id="20241223100000",
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.list_funds.return_value = mock_response
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        # assert "amc" not in call_args.kwargs  # implicit filter check

    @pytest.mark.asyncio
    async def test_list_funds_with_filters(self, client, mock_fund_service):
        """Test listing with filters."""
        mock_response = FundListResponse(
            items=[],
            next_cursor=None,
            as_of_date="2024-12-23",
            data_snapshot_id="123",
        )
        mock_service_instance = AsyncMock()
        mock_service_instance.list_funds.return_value = mock_response
        mock_fund_service.return_value = mock_service_instance
        
        # Test filters
        response = await client.get("/funds?amc=A&amc=B&category=EQ&risk=5&fee_band=low")
        assert response.status_code == 200
        
        call_args = mock_service_instance.list_funds.call_args
        filters = call_args.kwargs["filters"]
        assert filters["amc"] == ["A", "B"]
        assert filters["category"] == ["EQ"]
        assert filters["risk"] == ["5"]
        assert filters["fee_band"] == ["low"]

    @pytest.mark.asyncio
    async def test_list_funds_with_sort(self, client, mock_fund_service):
        """Test listing with sort."""
        mock_service_instance = AsyncMock()
        mock_service_instance.list_funds.return_value = FundListResponse(
            items=[], next_cursor=None, as_of_date="", data_snapshot_id=""
        )
        mock_fund_service.return_value = mock_service_instance

        response = await client.get("/funds?sort=fee_asc")
        assert response.status_code == 200
        
        call_args = mock_service_instance.list_funds.call_args
        assert call_args.kwargs["sort"] == "fee_asc"

    @pytest.mark.asyncio
    async def test_list_funds_with_cursor(self, client, mock_fund_service):
        """Test pagination with cursor."""
        mock_response = FundListResponse(
            items=[],
            next_cursor=None,
            as_of_date="2024-12-23",
            data_snapshot_id="20241223100000",
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.list_funds.return_value = mock_response
        mock_fund_service.return_value = mock_service_instance
        
        cursor = "eyJuIjoiVGVzdCBGdW5kIEIiLCJpIjoiTTAwMDJfMjAyNCJ9"
        response = await client.get(f"/funds?cursor={cursor}")
        
        assert response.status_code == 200
        call_args = mock_service_instance.list_funds.call_args
        assert call_args.kwargs["cursor"] == cursor

    @pytest.mark.asyncio
    async def test_list_funds_custom_limit(self, client, mock_fund_service):
        """Test custom limit parameter."""
        mock_response = FundListResponse(
            items=[],
            next_cursor=None,
            as_of_date="2024-12-23",
            data_snapshot_id="20241223100000",
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.list_funds.return_value = mock_response
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds?limit=50")
        
        assert response.status_code == 200
        mock_service_instance.list_funds.assert_called_once()
        call_args = mock_service_instance.list_funds.call_args
        assert call_args.kwargs.get("limit") == 50
    
    @pytest.mark.asyncio
    async def test_list_funds_limit_validation(self, client):
        """Test limit parameter validation."""
        # Limit too high - should be rejected by FastAPI validation
        response = await client.get("/funds?limit=200")
        assert response.status_code == 422  # Validation error
        
        # Limit too low
        response = await client.get("/funds?limit=0")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_list_funds_empty_result(self, client, mock_fund_service):
        """Test empty result set."""
        mock_response = FundListResponse(
            items=[],
            next_cursor=None,
            as_of_date="2024-12-23",
            data_snapshot_id="20241223100000",
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.list_funds.return_value = mock_response
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["next_cursor"] is None


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    @pytest.mark.asyncio
    async def test_root(self, client):
        """Test root endpoint returns API info."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestGetFundById:
    """Tests for GET /funds/{fund_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_fund_by_id_success(self, client, mock_fund_service):
        """Test successful fund detail retrieval."""
        from app.models.fund import FundDetail
        
        mock_fund = FundDetail(
            fund_id="M0001_2024",
            fund_name="Test Fund A",
            fund_abbr="TFA",
            category="Equity",
            amc_id="AMC001",
            amc_name="Test AMC",
            risk_level="5",
            expense_ratio=1.234,
            as_of_date="2024-12-23",
            last_updated_at="2024-12-23T10:00:00",
            data_source=None,
            data_version="20241223100000",
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_fund_by_id.return_value = mock_fund
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/M0001_2024")
        
        assert response.status_code == 200
        data = response.json()
        assert data["fund_id"] == "M0001_2024"
        assert data["fund_name"] == "Test Fund A"
        assert data["amc_name"] == "Test AMC"
        assert data["expense_ratio"] == 1.234  # Should be rounded to 3 decimals
        assert "as_of_date" in data or "last_updated_at" in data  # At least one freshness field
    
    @pytest.mark.asyncio
    async def test_get_fund_by_id_not_found(self, client, mock_fund_service):
        """Test 404 when fund not found."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_fund_by_id.side_effect = ValueError("Fund not found: M9999_2024")
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/M9999_2024")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_fund_by_id_invalid_empty(self, client, mock_fund_service):
        """Test 400 for empty fund_id."""
        # FastAPI path validation should catch this, but test the endpoint logic
        mock_service_instance = AsyncMock()
        mock_service_instance.get_fund_by_id.side_effect = ValueError("fund_id cannot be empty")
        mock_fund_service.return_value = mock_service_instance
        
        # Note: FastAPI won't allow empty path param, but we test with whitespace
        response = await client.get("/funds/   ")
        
        # Should be 400 or handled by FastAPI validation
        assert response.status_code in [400, 404]  # FastAPI might return 404 for invalid path
    
    @pytest.mark.asyncio
    async def test_get_fund_by_id_expense_ratio_rounding(self, client, mock_fund_service):
        """Test expense_ratio is rounded to 3 decimals."""
        from app.models.fund import FundDetail
        
        mock_fund = FundDetail(
            fund_id="M0002_2024",
            fund_name="Test Fund B",
            fund_abbr=None,
            category="Bond",
            amc_id="AMC002",
            amc_name="Test AMC 2",
            risk_level=None,
            expense_ratio=1.234567,  # Should be rounded to 1.235
            as_of_date="2024-12-23",
            last_updated_at="2024-12-23T10:00:00",
            data_source=None,
            data_version=None,
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_fund_by_id.return_value = mock_fund
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/M0002_2024")
        
        assert response.status_code == 200
        data = response.json()
        # Verify rounding to 3 decimals
        assert data["expense_ratio"] == 1.235
    
    @pytest.mark.asyncio
    async def test_get_fund_by_id_nullable_fields(self, client, mock_fund_service):
        """Test that nullable fields are handled correctly."""
        from app.models.fund import FundDetail
        
        mock_fund = FundDetail(
            fund_id="M0003_2024",
            fund_name="Test Fund C",
            fund_abbr=None,
            category="Mixed",
            amc_id="AMC003",
            amc_name="Test AMC 3",
            risk_level=None,
            expense_ratio=None,
            as_of_date="2024-12-23",
            last_updated_at="2024-12-23T10:00:00",
            data_source=None,
            data_version=None,
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_fund_by_id.return_value = mock_fund
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/M0003_2024")
        
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] is None
        assert data["expense_ratio"] is None
        assert data["fund_abbr"] is None
