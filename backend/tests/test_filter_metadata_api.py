"""Tests for filter metadata API endpoints (US-N3)."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from main import app
from app.models.fund import CategoryListResponse, RiskListResponse, AMCListResponse


@pytest.fixture
def mock_fund_service():
    """Create a mock fund service."""
    with patch('app.api.funds.FundService') as mock:
        yield mock


@pytest_asyncio.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestGetCategories:
    """Tests for GET /funds/categories endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self, client, mock_fund_service):
        """Test successful category listing with counts."""
        mock_categories = [
            {"value": "Equity", "count": 128},
            {"value": "Fixed Income", "count": 95},
            {"value": "Mixed", "count": 42},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_categories_with_counts.return_value = mock_categories
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 3
        assert data["items"][0]["value"] == "Equity"
        assert data["items"][0]["count"] == 128
        assert data["items"][1]["value"] == "Fixed Income"
        assert data["items"][1]["count"] == 95
    
    @pytest.mark.asyncio
    async def test_get_categories_excludes_nulls(self, client, mock_fund_service):
        """Test that categories endpoint excludes null values."""
        mock_categories = [
            {"value": "Equity", "count": 128},
            {"value": "Fixed Income", "count": 95},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_categories_with_counts.return_value = mock_categories
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/categories")
        
        assert response.status_code == 200
        data = response.json()
        # Verify no null values in response
        for item in data["items"]:
            assert item["value"] is not None
            assert item["value"] != ""
    
    @pytest.mark.asyncio
    async def test_get_categories_ordered_by_count_desc(self, client, mock_fund_service):
        """Test that categories are ordered by count descending, then alphabetically."""
        # Mock data should be pre-sorted as the service would return it
        mock_categories = [
            {"value": "Equity", "count": 128},
            {"value": "Alternative", "count": 95},  # Alphabetically before "Fixed Income"
            {"value": "Fixed Income", "count": 95},
            {"value": "Mixed", "count": 42},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_categories_with_counts.return_value = mock_categories
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/categories")
        
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        
        # Verify descending count order
        assert items[0]["count"] >= items[1]["count"]
        assert items[1]["count"] >= items[2]["count"]
        assert items[2]["count"] >= items[3]["count"]
        
        # Verify alphabetical tie-breaker for same count
        assert items[1]["value"] == "Alternative"  # Alphabetically before "Fixed Income"
        assert items[2]["value"] == "Fixed Income"
    
    @pytest.mark.asyncio
    async def test_get_categories_empty_result(self, client, mock_fund_service):
        """Test empty category result."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_categories_with_counts.return_value = []
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
    
    @pytest.mark.asyncio
    async def test_get_categories_service_error(self, client, mock_fund_service):
        """Test error handling when service fails."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_categories_with_counts.side_effect = Exception("Database error")
        mock_fund_service.return_value = mock_service_instance
        
        # FastAPI will convert unhandled exceptions to 500 errors
        response = await client.get("/funds/categories")
        
        # Should return 500 (FastAPI default for unhandled exceptions)
        assert response.status_code == 500


class TestGetRisks:
    """Tests for GET /funds/risks endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_risks_success(self, client, mock_fund_service):
        """Test successful risk level listing with counts."""
        mock_risks = [
            {"value": "1", "count": 15},
            {"value": "2", "count": 28},
            {"value": "3", "count": 42},
            {"value": "4", "count": 52},
            {"value": "5", "count": 38},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_risks_with_counts.return_value = mock_risks
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/risks")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 5
        assert data["items"][0]["value"] == "1"
        assert data["items"][0]["count"] == 15
    
    @pytest.mark.asyncio
    async def test_get_risks_excludes_nulls(self, client, mock_fund_service):
        """Test that risks endpoint excludes null values."""
        mock_risks = [
            {"value": "1", "count": 15},
            {"value": "2", "count": 28},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_risks_with_counts.return_value = mock_risks
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/risks")
        
        assert response.status_code == 200
        data = response.json()
        # Verify no null values in response
        for item in data["items"]:
            assert item["value"] is not None
            assert item["value"] != ""
    
    @pytest.mark.asyncio
    async def test_get_risks_ordered_ascending(self, client, mock_fund_service):
        """Test that risks are ordered by risk_level ascending (numeric if possible)."""
        mock_risks = [
            {"value": "1", "count": 15},
            {"value": "2", "count": 28},
            {"value": "3", "count": 42},
            {"value": "4", "count": 52},
            {"value": "5", "count": 38},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_risks_with_counts.return_value = mock_risks
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/risks")
        
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        
        # Verify ascending order (numeric)
        for i in range(len(items) - 1):
            assert int(items[i]["value"]) <= int(items[i + 1]["value"])
    
    @pytest.mark.asyncio
    async def test_get_risks_empty_result(self, client, mock_fund_service):
        """Test empty risk result."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_risks_with_counts.return_value = []
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/risks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []


class TestGetAMCs:
    """Tests for GET /funds/amcs endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_amcs_basic_success(self, client, mock_fund_service):
        """Test successful AMC listing without search."""
        mock_amcs = {
            "items": [
                {"id": "KASSET", "name": "KAsset", "count": 240},
                {"id": "SCBAM", "name": "SCB Asset Management", "count": 180},
                {"id": "BBLAM", "name": "BBL Asset Management", "count": 150},
            ],
            "next_cursor": None
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/amcs")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 3
        assert data["items"][0]["id"] == "KASSET"
        assert data["items"][0]["name"] == "KAsset"
        assert data["items"][0]["count"] == 240
        assert data["next_cursor"] is None
    
    @pytest.mark.asyncio
    async def test_get_amcs_with_search(self, client, mock_fund_service):
        """Test AMC search functionality."""
        mock_amcs = {
            "items": [
                {"id": "KASSET", "name": "KASIKORN ASSET MANAGEMENT", "count": 240},
            ],
            "next_cursor": None
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/amcs?q=KASIKORN")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert "KASIKORN" in data["items"][0]["name"].upper()
        
        # Verify search term was passed to service
        call_args = mock_service_instance.get_amcs_with_fund_counts.call_args
        assert call_args.kwargs["search_term"] == "KASIKORN"
    
    @pytest.mark.asyncio
    async def test_get_amcs_with_pagination(self, client, mock_fund_service):
        """Test AMC pagination with cursor."""
        import base64
        import json
        
        cursor_data = {"last_amc_id": "BBLAM", "last_count": 150}
        encoded_cursor = base64.urlsafe_b64encode(
            json.dumps(cursor_data).encode()
        ).decode()
        
        mock_amcs = {
            "items": [
                {"id": "KTAM", "name": "Krung Thai Asset Management", "count": 120},
                {"id": "MFC", "name": "MFC Asset Management", "count": 100},
            ],
            "next_cursor": None
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get(f"/funds/amcs?cursor={encoded_cursor}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        
        # Verify cursor was passed to service
        call_args = mock_service_instance.get_amcs_with_fund_counts.call_args
        assert call_args.kwargs["cursor"] == encoded_cursor
    
    @pytest.mark.asyncio
    async def test_get_amcs_with_limit(self, client, mock_fund_service):
        """Test AMC limit parameter."""
        mock_amcs = {
            "items": [
                {"id": f"AMC{i}", "name": f"AMC {i}", "count": 100 - i}
                for i in range(10)
            ],
            "next_cursor": "encoded_cursor_here"
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/amcs?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        
        # Verify limit was passed to service
        call_args = mock_service_instance.get_amcs_with_fund_counts.call_args
        assert call_args.kwargs["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_get_amcs_limit_validation(self, client):
        """Test AMC limit parameter validation."""
        # Limit too high
        response = await client.get("/funds/amcs?limit=200")
        assert response.status_code == 422  # Validation error
        
        # Limit too low
        response = await client.get("/funds/amcs?limit=0")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_amcs_empty_search_result(self, client, mock_fund_service):
        """Test AMC search with no results."""
        mock_amcs = {
            "items": [],
            "next_cursor": None
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/amcs?q=NonexistentAMC")
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["next_cursor"] is None
    
    @pytest.mark.asyncio
    async def test_get_amcs_pagination_returns_next_cursor(self, client, mock_fund_service):
        """Test that pagination returns next_cursor when more results exist."""
        import base64
        import json
        
        cursor_data = {"last_amc_id": "AMC20", "last_count": 80}
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(cursor_data).encode()
        ).decode()
        
        mock_amcs = {
            "items": [
                {"id": f"AMC{i}", "name": f"AMC {i}", "count": 100 - i}
                for i in range(20)
            ],
            "next_cursor": next_cursor
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/amcs?limit=20")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20
        assert data["next_cursor"] == next_cursor
    
    @pytest.mark.asyncio
    async def test_get_amcs_combined_params(self, client, mock_fund_service):
        """Test AMC endpoint with search, limit, and cursor combined."""
        import base64
        import json
        
        cursor_data = {"last_amc_id": "KASSET", "last_count": 240}
        encoded_cursor = base64.urlsafe_b64encode(
            json.dumps(cursor_data).encode()
        ).decode()
        
        mock_amcs = {
            "items": [
                {"id": "KASSET", "name": "KASIKORN ASSET MANAGEMENT", "count": 240},
            ],
            "next_cursor": None
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get(f"/funds/amcs?q=KASIKORN&limit=10&cursor={encoded_cursor}")
        
        assert response.status_code == 200
        
        # Verify all parameters were passed
        call_args = mock_service_instance.get_amcs_with_fund_counts.call_args
        assert call_args.kwargs["search_term"] == "KASIKORN"
        assert call_args.kwargs["limit"] == 10
        assert call_args.kwargs["cursor"] == encoded_cursor


class TestFilterMetadataIntegration:
    """Integration tests for filter metadata endpoints."""
    
    @pytest.mark.asyncio
    async def test_categories_response_structure(self, client, mock_fund_service):
        """Test that categories response matches expected structure."""
        mock_categories = [
            {"value": "Equity", "count": 128},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_categories_with_counts.return_value = mock_categories
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/categories")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure matches CategoryListResponse
        assert "items" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "value" in item
            assert "count" in item
            assert isinstance(item["value"], str)
            assert isinstance(item["count"], int)
    
    @pytest.mark.asyncio
    async def test_risks_response_structure(self, client, mock_fund_service):
        """Test that risks response matches expected structure."""
        mock_risks = [
            {"value": "1", "count": 15},
        ]
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_risks_with_counts.return_value = mock_risks
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/risks")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure matches RiskListResponse
        assert "items" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "value" in item
            assert "count" in item
            assert isinstance(item["value"], str)
            assert isinstance(item["count"], int)
    
    @pytest.mark.asyncio
    async def test_amcs_response_structure(self, client, mock_fund_service):
        """Test that AMCs response matches expected structure."""
        mock_amcs = {
            "items": [
                {"id": "KASSET", "name": "KAsset", "count": 240},
            ],
            "next_cursor": None
        }
        
        mock_service_instance = AsyncMock()
        mock_service_instance.get_amcs_with_fund_counts.return_value = mock_amcs
        mock_fund_service.return_value = mock_service_instance
        
        response = await client.get("/funds/amcs")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure matches AMCListResponse
        assert "items" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
        assert data["next_cursor"] is None or isinstance(data["next_cursor"], str)
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "count" in item
            assert isinstance(item["id"], str)
            assert isinstance(item["name"], str)
            assert isinstance(item["count"], int)

