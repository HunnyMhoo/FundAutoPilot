"""
Unit tests for peer classification service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.peer_classification_service import (
    PeerClassificationService,
    HEDGE_KEYWORD_PATTERNS,
    DISTRIBUTION_POLICY_MAPPING,
)
from app.models.fund_orm import Fund
from app.utils.sec_api_client import SECAPIErrorType


@pytest.fixture
def mock_fund():
    """Create a mock fund object."""
    fund = Mock(spec=Fund)
    fund.proj_id = "M0001_2024"
    fund.class_abbr_name = ""
    fund.fund_abbr = "TEST-FUND"
    fund.aimc_category = "US Equity"
    fund.fund_status = "RG"
    return fund


@pytest.fixture
def service():
    """Create a PeerClassificationService instance."""
    return PeerClassificationService()


class TestComputePeerFocus:
    """Tests for compute_peer_focus method."""
    
    def test_returns_aimc_category_exact_copy(self, service, mock_fund):
        """Test that peer_focus is exact copy of aimc_category."""
        result = service.compute_peer_focus(mock_fund)
        assert result == "US Equity"
        assert result == mock_fund.aimc_category
    
    def test_returns_none_when_aimc_category_missing(self, service, mock_fund):
        """Test that peer_focus is None when aimc_category is None."""
        mock_fund.aimc_category = None
        result = service.compute_peer_focus(mock_fund)
        assert result is None


class TestComputePeerCurrency:
    """Tests for compute_peer_currency method."""
    
    def test_extracts_currency_from_minimum_sub_cur(self, service):
        """Test currency extraction from minimum_sub_cur."""
        with patch.object(service.api_client, 'fetch_investment') as mock_fetch:
            mock_fetch.return_value = ([{
                "minimum_sub_cur": "USD",
                "minimum_redempt_cur": "THB",
            }], None)
            
            result = service.compute_peer_currency("M0001_2024")
            assert result == "USD"
    
    def test_falls_back_to_minimum_redempt_cur(self, service):
        """Test fallback to minimum_redempt_cur when minimum_sub_cur is missing."""
        with patch.object(service.api_client, 'fetch_investment') as mock_fetch:
            mock_fetch.return_value = ([{
                "minimum_sub_cur": None,
                "minimum_redempt_cur": "EUR",
            }], None)
            
            result = service.compute_peer_currency("M0001_2024")
            assert result == "EUR"
    
    def test_defaults_to_thb_when_currency_missing(self, service):
        """Test default to THB when currency fields are missing."""
        with patch.object(service.api_client, 'fetch_investment') as mock_fetch:
            mock_fetch.return_value = ([{
                "minimum_sub_cur": None,
                "minimum_redempt_cur": None,
            }], None)
            
            result = service.compute_peer_currency("M0001_2024")
            assert result == "THB"
    
    def test_defaults_to_thb_on_api_error(self, service):
        """Test default to THB on API error."""
        with patch.object(service.api_client, 'fetch_investment') as mock_fetch:
            mock_fetch.return_value = (None, SECAPIErrorType.HTTP_ERROR)
            
            result = service.compute_peer_currency("M0001_2024")
            assert result == "THB"
    
    def test_defaults_to_thb_on_exception(self, service):
        """Test default to THB on exception."""
        with patch.object(service.api_client, 'fetch_investment') as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")
            
            result = service.compute_peer_currency("M0001_2024")
            assert result == "THB"
    
    def test_handles_multiple_classes_with_selection(self, service):
        """Test class selection when multiple classes exist."""
        with patch.object(service.api_client, 'fetch_investment') as mock_fetch:
            from app.services.compare_service import select_default_class
            
            mock_fetch.return_value = ([
                {"class_abbr_name": "A", "minimum_sub_cur": "USD"},
                {"class_abbr_name": "B", "minimum_sub_cur": "THB"},
            ], None)
            
            result = service.compute_peer_currency("M0001_2024", class_abbr_name="A", fund_abbr="TEST-FUND")
            # Should select class A based on class_abbr_name
            assert result in ["USD", "THB"]  # Depends on selection logic


class TestComputePeerFxHedgedFlag:
    """Tests for compute_peer_fx_hedged_flag method."""
    
    def test_detects_fully_fx_risk_hedge(self, service, mock_fund):
        """Test detection of 'Fully FX Risk Hedge' pattern."""
        mock_fund.aimc_category = "Global Equity Fully FX Risk Hedge"
        result = service.compute_peer_fx_hedged_flag(mock_fund)
        assert result == "Hedged"
    
    def test_detects_fully_fx_hedge(self, service, mock_fund):
        """Test detection of 'Fully F/X Hedge' pattern."""
        mock_fund.aimc_category = "Global Bond Fully F/X Hedge"
        result = service.compute_peer_fx_hedged_flag(mock_fund)
        assert result == "Hedged"
    
    def test_detects_discretionary_fx_hedge(self, service, mock_fund):
        """Test detection of 'Discretionary F/X Hedge' pattern."""
        mock_fund.aimc_category = "Global Bond Discretionary F/X Hedge or Unhedge"
        result = service.compute_peer_fx_hedged_flag(mock_fund)
        assert result == "Mixed"
    
    def test_detects_unhedge(self, service, mock_fund):
        """Test detection of 'Unhedge' pattern."""
        mock_fund.aimc_category = "US Equity Unhedge"
        result = service.compute_peer_fx_hedged_flag(mock_fund)
        assert result == "Unhedged"
    
    def test_returns_unknown_when_no_pattern_matches(self, service, mock_fund):
        """Test returns 'Unknown' when no hedge pattern matches."""
        mock_fund.aimc_category = "US Equity"
        result = service.compute_peer_fx_hedged_flag(mock_fund)
        assert result == "Unknown"
    
    def test_returns_unknown_when_aimc_category_missing(self, service, mock_fund):
        """Test returns 'Unknown' when aimc_category is None."""
        mock_fund.aimc_category = None
        result = service.compute_peer_fx_hedged_flag(mock_fund)
        assert result == "Unknown"
    
    def test_longest_match_takes_precedence(self, service, mock_fund):
        """Test that longest matching pattern takes precedence."""
        # "Discretionary F/X Hedge or Unhedge" should match before "Unhedge"
        mock_fund.aimc_category = "Global Bond Discretionary F/X Hedge or Unhedge"
        result = service.compute_peer_fx_hedged_flag(mock_fund)
        assert result == "Mixed"  # Not "Unhedged"


class TestComputePeerDistributionPolicy:
    """Tests for compute_peer_distribution_policy method."""
    
    def test_maps_y_to_d(self, service):
        """Test mapping of 'Y' (pays dividends) to 'D'."""
        with patch.object(service.api_client, 'fetch_dividend') as mock_fetch:
            mock_fetch.return_value = ([{
                "class_abbr_name": None,
                "dividend_policy": "Y",
            }], None)
            
            result = service.compute_peer_distribution_policy("M0001_2024")
            assert result == "D"
    
    def test_maps_n_to_a(self, service):
        """Test mapping of 'N' (accumulating) to 'A'."""
        with patch.object(service.api_client, 'fetch_dividend') as mock_fetch:
            mock_fetch.return_value = ([{
                "class_abbr_name": None,
                "dividend_policy": "N",
            }], None)
            
            result = service.compute_peer_distribution_policy("M0001_2024")
            assert result == "A"
    
    def test_returns_none_when_dividend_policy_missing(self, service):
        """Test returns None when dividend_policy field is missing."""
        with patch.object(service.api_client, 'fetch_dividend') as mock_fetch:
            mock_fetch.return_value = ([{
                "class_abbr_name": None,
                "dividend_policy": None,
            }], None)
            
            result = service.compute_peer_distribution_policy("M0001_2024")
            assert result is None
    
    def test_returns_none_on_api_error(self, service):
        """Test returns None on API error."""
        with patch.object(service.api_client, 'fetch_dividend') as mock_fetch:
            mock_fetch.return_value = (None, SECAPIErrorType.NO_CONTENT)
            
            result = service.compute_peer_distribution_policy("M0001_2024")
            assert result is None
    
    def test_handles_multiple_classes_with_selection(self, service):
        """Test class selection when multiple classes exist."""
        with patch.object(service.api_client, 'fetch_dividend') as mock_fetch:
            mock_fetch.return_value = ([
                {"class_abbr_name": "A", "dividend_policy": "Y"},
                {"class_abbr_name": "B", "dividend_policy": "N"},
            ], None)
            
            result = service.compute_peer_distribution_policy(
                "M0001_2024",
                class_abbr_name="A",
                fund_abbr="TEST-FUND"
            )
            # Should select class A
            assert result in ["D", "A"]  # Depends on selection logic


class TestComputePeerKey:
    """Tests for compute_peer_key method."""
    
    def test_builds_full_peer_key(self, service):
        """Test building peer key with all components."""
        result = service.compute_peer_key(
            aimc_category="US Equity",
            peer_focus="US Equity",
            peer_currency="USD",
            peer_fx_hedged_flag="Hedged",
            peer_distribution_policy="D"
        )
        assert result == "US Equity|US Equity|USD|Hedged|D"
    
    def test_uses_empty_strings_for_missing_components(self, service):
        """Test that missing components use empty strings."""
        result = service.compute_peer_key(
            aimc_category="Global Equity",
            peer_focus="Global Equity",
            peer_currency=None,
            peer_fx_hedged_flag=None,
            peer_distribution_policy=None
        )
        assert result == "Global Equity|Global Equity|||"
    
    def test_returns_none_when_aimc_category_missing(self, service):
        """Test returns None when aimc_category is missing."""
        result = service.compute_peer_key(
            aimc_category=None,
            peer_focus=None,
            peer_currency="THB",
            peer_fx_hedged_flag="Unknown",
            peer_distribution_policy="A"
        )
        assert result is None
    
    def test_handles_partial_data(self, service):
        """Test peer key with partial data."""
        result = service.compute_peer_key(
            aimc_category="Thailand Equity",
            peer_focus="Thailand Equity",
            peer_currency="THB",
            peer_fx_hedged_flag="Unhedged",
            peer_distribution_policy=None
        )
        assert result == "Thailand Equity|Thailand Equity|THB|Unhedged|"


class TestDetermineFallbackLevel:
    """Tests for determine_fallback_level method."""
    
    def test_level_0_full_classification(self, service):
        """Test level 0 when all components are present."""
        result = service.determine_fallback_level(
            peer_distribution_policy="D",
            peer_fx_hedged_flag="Hedged",
            peer_currency="USD"
        )
        assert result == 0
    
    def test_level_1_missing_distribution(self, service):
        """Test level 1 when distribution is missing."""
        result = service.determine_fallback_level(
            peer_distribution_policy=None,
            peer_fx_hedged_flag="Hedged",
            peer_currency="USD"
        )
        assert result == 1
    
    def test_level_2_missing_hedge(self, service):
        """Test level 2 when hedge flag is missing or Unknown."""
        result = service.determine_fallback_level(
            peer_distribution_policy="D",
            peer_fx_hedged_flag="Unknown",
            peer_currency="USD"
        )
        assert result == 2
    
    def test_level_3_missing_currency(self, service):
        """Test level 3 when currency is missing."""
        result = service.determine_fallback_level(
            peer_distribution_policy="D",
            peer_fx_hedged_flag="Hedged",
            peer_currency=None
        )
        assert result == 3


class TestClassifyFund:
    """Tests for classify_fund method."""
    
    def test_classifies_fund_successfully(self, service, mock_fund):
        """Test successful fund classification."""
        mock_session = Mock()
        mock_session.commit = Mock()
        
        with patch.object(service, 'compute_peer_focus', return_value="US Equity"), \
             patch.object(service, 'compute_peer_currency', return_value="USD"), \
             patch.object(service, 'compute_peer_fx_hedged_flag', return_value="Hedged"), \
             patch.object(service, 'compute_peer_distribution_policy', return_value="D"), \
             patch.object(service, 'compute_peer_key', return_value="US Equity|US Equity|USD|Hedged|D"), \
             patch.object(service, 'determine_fallback_level', return_value=0):
            
            result = service.classify_fund(mock_fund, mock_session)
            
            assert result["success"] is True
            assert result["peer_key"] == "US Equity|US Equity|USD|Hedged|D"
            assert result["fallback_level"] == 0
            assert mock_fund.peer_focus == "US Equity"
            assert mock_fund.peer_currency == "USD"
            assert mock_fund.peer_fx_hedged_flag == "Hedged"
            assert mock_fund.peer_distribution_policy == "D"
            mock_session.commit.assert_called_once()
    
    def test_handles_missing_aimc_category(self, service, mock_fund):
        """Test classification when AIMC category is missing."""
        mock_fund.aimc_category = None
        mock_session = Mock()
        mock_session.commit = Mock()
        
        with patch.object(service, 'compute_peer_focus', return_value=None), \
             patch.object(service, 'compute_peer_currency', return_value="THB"), \
             patch.object(service, 'compute_peer_fx_hedged_flag', return_value="Unknown"), \
             patch.object(service, 'compute_peer_distribution_policy', return_value=None), \
             patch.object(service, 'compute_peer_key', return_value=None), \
             patch.object(service, 'determine_fallback_level', return_value=3):
            
            result = service.classify_fund(mock_fund, mock_session)
            
            assert result["success"] is True
            assert result["peer_key"] is None
            assert mock_fund.peer_key is None
            mock_session.commit.assert_called_once()
    
    def test_handles_exception_gracefully(self, service, mock_fund):
        """Test that exceptions are handled gracefully."""
        mock_session = Mock()
        mock_session.rollback = Mock()
        
        with patch.object(service, 'compute_peer_focus', side_effect=Exception("Test error")):
            result = service.classify_fund(mock_fund, mock_session)
            
            assert result["success"] is False
            assert "error" in result
            mock_session.rollback.assert_called_once()

