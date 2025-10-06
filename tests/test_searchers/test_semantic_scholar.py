"""
Pytest-style tests for the semantic_scholar.py searcher module.

This test suite verifies the functionality of the SemanticScholarSearcher class, including
initialization with and without an API key, query construction, API response parsing,
filtering, caching, and comprehensive error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from research_finder.searchers.semantic_scholar import SemanticScholarSearcher
import requests.exceptions

# --- Mock Data for Semantic Scholar API Response ---

@pytest.fixture
def sample_semantic_scholar_response():
    """A mock JSON response from the Semantic Scholar API."""
    return {
        "data": [
            {
                "title": "  Attention Is All You Need  ",
                "authors": [{"name": "Ashish Vaswani"}, {"name": "  Noam Shazeer  "}],
                "year": 2017,
                "url": "https://www.semanticscholar.org/paper/Attention-Is-All-You-Need/Vaswani/123456",
                "citationCount": 50000,
                "venue": "NeurIPS",
                "openAccessPdf": {"license": "arXiv"},
                "externalIds": {"DOI": "10.1001/nips.2017.123456"}
            },
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "authors": [{"name": "Jacob Devlin"}, {"name": "Ming-Wei Chang"}],
                "year": 2018,
                "url": "https://www.semanticscholar.org/paper/BERT/Devlin/7891011",
                "citationCount": 75000,
                "venue": None, # Test missing venue
                "openAccessPdf": {}, # Test empty openAccessPdf
                "externalIds": {"ArXiv": "1810.04805"} # Test missing DOI
            }
        ]
    }

@pytest.fixture
def semantic_scholar_searcher_with_key(mock_cache_manager):
    """Provides a SemanticScholarSearcher instance with an API key."""
    with patch('research_finder.searchers.semantic_scholar.S2_API_KEY', 'TEST_S2_KEY'):
        return SemanticScholarSearcher(cache_manager=mock_cache_manager)

@pytest.fixture
def semantic_scholar_searcher_no_key(mock_cache_manager):
    """Provides a SemanticScholarSearcher instance without an API key."""
    with patch('research_finder.searchers.semantic_scholar.S2_API_KEY', None):
        return SemanticScholarSearcher(cache_manager=mock_cache_manager)

# --- Test Suite ---

class TestSemanticScholarSearcher:
    """Test suite for the SemanticScholarSearcher class."""

    def test_init_with_key_sets_correct_rate_limit(self, semantic_scholar_searcher_with_key):
        """Test that providing an API key sets the correct rate limit."""
        assert semantic_scholar_searcher_with_key.name == "Semantic Scholar"
        assert semantic_scholar_searcher_with_key.api_key == 'TEST_S2_KEY'
        assert semantic_scholar_searcher_with_key.rate_limit == 1.0 # Polite limit

    def test_init_without_key_sets_correct_rate_limit(self, semantic_scholar_searcher_no_key):
        """Test that not providing an API key sets the unpolite rate limit."""
        assert semantic_scholar_searcher_no_key.api_key is None
        assert semantic_scholar_searcher_no_key.rate_limit == 0.1 # Unpolite limit

    @patch('research_finder.searchers.semantic_scholar.requests.get')
    def test_search_keyword_query(self, mock_get, semantic_scholar_searcher_with_key, sample_semantic_scholar_response):
        """Test a standard keyword search and data parsing."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_semantic_scholar_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        semantic_scholar_searcher_with_key.search("transformers", limit=10)

        # Assert the API was called with the correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['query'] == 'transformers'
        assert call_args[1]['params']['limit'] == 10
        assert call_args[1]['headers']['x-api-key'] == 'TEST_S2_KEY'

        # Assert the results were parsed and stored correctly
        assert len(semantic_scholar_searcher_with_key.results) == 2
        result1 = semantic_scholar_searcher_with_key.results[0]
        assert result1['Title'] == 'Attention Is All You Need'
        assert result1['Authors'] == 'Ashish Vaswani, Noam Shazeer'
        assert result1['Year'] == '2017'
        assert result1['Venue'] == 'NeurIPS'
        assert result1['Source'] == 'Semantic Scholar'
        assert result1['Citation Count'] == 50000
        assert result1['DOI'] == '10.1001/nips.2017.123456'
        assert result1['License Type'] == 'arXiv'
        assert result1['URL'] == 'https://www.semanticscholar.org/paper/Attention-Is-All-You-Need/Vaswani/123456'

        result2 = semantic_scholar_searcher_with_key.results[1]
        assert result2['Title'] == 'BERT: Pre-training of Deep Bidirectional Transformers'
        assert result2['Venue'] == 'N/A' # Handles missing venue
        assert result2['License Type'] == 'N/A' # Handles empty license
        assert result2['DOI'] == 'N/A' # Handles missing DOI

    @patch('research_finder.searchers.semantic_scholar.requests.get')
    def test_search_title_and_author_queries(self, mock_get, semantic_scholar_searcher_with_key, sample_semantic_scholar_response):
        """Test that title and author search terms are constructed correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_semantic_scholar_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Test title search
        semantic_scholar_searcher_with_key.search("Attention Is All You Need", search_type='title')
        call_args = mock_get.call_args
        assert call_args[1]['params']['query'] == '"Attention Is All You Need"'

        # Test author search
        semantic_scholar_searcher_with_key.search("Ashish Vaswani", search_type='author')
        call_args = mock_get.call_args
        assert call_args[1]['params']['query'] == 'author:"Ashish Vaswani"'

    @patch('research_finder.searchers.semantic_scholar.requests.get')
    def test_search_with_filters(self, mock_get, semantic_scholar_searcher_with_key, sample_semantic_scholar_response):
        """Test that year and citation filters are applied correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_semantic_scholar_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        filters = {'year_min': '2017', 'year_max': '2018', 'min_citations': 1000}
        semantic_scholar_searcher_with_key.search("transformers", filters=filters)

        params = mock_get.call_args[1]['params']
        assert params['year'] == '2017-2018'
        assert params['minCitationCount'] == 1000

    def test_search_uses_cache_on_hit(self, semantic_scholar_searcher_with_key, mock_cache_manager):
        """Test that the searcher returns cached results if they exist."""
        cached_data = [{'Title': 'Cached Paper'}]
        mock_cache_manager.get.return_value = cached_data

        semantic_scholar_searcher_with_key.search("test query", 10)

        mock_cache_manager.get.assert_called_once()
        with patch('research_finder.searchers.semantic_scholar.requests.get') as mock_get:
            semantic_scholar_searcher_with_key.search("test query", 10)
            mock_get.assert_not_called()
        assert semantic_scholar_searcher_with_key.results == cached_data

    @patch('research_finder.searchers.semantic_scholar.requests.get')
    def test_search_saves_to_cache_on_miss(
        self, 
        mock_get,  # Keep this mock
        semantic_scholar_searcher_with_key,  # Use the correct searcher fixture
        sample_semantic_scholar_response,    # Use the correct data fixture
        mock_cache_manager
    ):
        """Test that new results are saved to the cache after a successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_semantic_scholar_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        mock_cache_manager.get.return_value = None

        semantic_scholar_searcher_with_key.search("test query", 10)

        mock_cache_manager.set.assert_called_once()
        args, _ = mock_cache_manager.set.call_args
        assert len(args[3]) == 2

    @patch('research_finder.searchers.semantic_scholar.requests.get')
    def test_search_handles_timeout(self, mock_get, semantic_scholar_searcher_with_key, caplog):
        """Test that request timeouts are caught and logged gracefully."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        semantic_scholar_searcher_with_key.search("slow query", 10)

        assert semantic_scholar_searcher_with_key.results == []
        assert "Request to Semantic Scholar API timed out" in caplog.text

    @patch('research_finder.searchers.semantic_scholar.requests.get')
    def test_search_handles_http_errors(self, mock_get, semantic_scholar_searcher_with_key, caplog):
        """Test that specific HTTP errors are caught and logged with detail."""
        # Test 401 Unauthorized
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        http_error_401 = requests.exceptions.HTTPError("401 Unauthorized")
        http_error_401.response = mock_response_401
        mock_get.return_value = mock_response_401
        mock_response_401.raise_for_status.side_effect = http_error_401

        semantic_scholar_searcher_with_key.search("query", 10)
        assert "Authentication failed. Please check your Semantic Scholar API key." in caplog.text

        # Test 429 Rate Limit
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '60'}
        http_error_429 = requests.exceptions.HTTPError("429 Too Many Requests")
        http_error_429.response = mock_response_429
        mock_get.return_value = mock_response_429
        mock_response_429.raise_for_status.side_effect = http_error_429

        semantic_scholar_searcher_with_key.search("query", 10)
        assert "Rate limit exceeded. Retry after 60 seconds." in caplog.text

        # Test 400 Bad Request
        mock_response_400 = MagicMock()
        mock_response_400.status_code = 400
        mock_response_400.json.return_value = {'error': 'Invalid year format'}
        http_error_400 = requests.exceptions.HTTPError("400 Bad Request")
        http_error_400.response = mock_response_400
        mock_get.return_value = mock_response_400
        mock_response_400.raise_for_status.side_effect = http_error_400

        semantic_scholar_searcher_with_key.search("query", 10)
        assert "Bad Request: {'error': 'Invalid year format'}" in caplog.text

    @patch('research_finder.searchers.semantic_scholar.requests.get')
    def test_enforces_rate_limit(self, mock_get, semantic_scholar_searcher_with_key, sample_semantic_scholar_response):
        """Test that the searcher calls its rate limiting method."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_semantic_scholar_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(semantic_scholar_searcher_with_key, '_enforce_rate_limit') as mock_rate_limit:
            semantic_scholar_searcher_with_key.search("test query", 10)
            mock_rate_limit.assert_called_once()