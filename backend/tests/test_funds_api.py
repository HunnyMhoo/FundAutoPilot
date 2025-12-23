"""Tests for Fund API endpoints."""

import pytest
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


@pytest.fixture
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
                FundSummary(
                    fund_id="M0002_2024",
                    fund_name="Test Fund B",
                    amc_name="Test AMC",
                    category=None,
                    risk_level=None,
                    expense_ratio=None,
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
        assert len(data["items"]) == 2
        assert data["next_cursor"] is not None
        assert data["as_of_date"] == "2024-12-23"
    
    @pytest.mark.asyncio
    async def test_list_funds_with_cursor(self, client, mock_fund_service):
        """Test pagination with cursor."""
        mock_response = FundListResponse(
            items=[
                FundSummary(
                    fund_id="M0003_2024",
                    fund_name="Test Fund C",
                    amc_name="Test AMC",
                    category="Fixed Income",
                    risk_level="2",
                    expense_ratio=0.5,
                ),
            ],
            next_cursor=None,  # End of results
            as_of_date="2024-12-23",
            data_snapshot_id="20241223100000",
        )
        
        mock_service_instance = AsyncMock()
        mock_service_instance.list_funds.return_value = mock_response
        mock_fund_service.return_value = mock_service_instance
        
        cursor = "eyJuIjoiVGVzdCBGdW5kIEIiLCJpIjoiTTAwMDJfMjAyNCJ9"
        response = await client.get(f"/funds?cursor={cursor}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["next_cursor"] is None  # End of results
    
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
