# tests/test_searchers/test_crossref.py
"""
Pytest-style tests for the crossref.py searcher module.

This test suite verifies the functionality of the CrossrefSearcher class, including
initialization with and without a 'mailto' email, query construction, API response
parsing, post-search filtering, caching, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from research_finder.searchers.crossref import CrossrefSearcher
import requests.exceptions

# --- Mock Data for CrossRef API Response ---

@pytest.fixture
def sample_crossref_api_response():
    """A mock JSON response from the CrossRef API."""
    return {
        "message": {
            "items": [
                {
                    "title": ["  A Comprehensive Study on Neural Networks  "],
                    "author": [
                        {"given": "John", "family": "Doe"},
                        {"given": "Jane", "family": "Smith"},
                        {"family": "Unknown"} # Author with no given name
                    ],
                    "container-title": ["Journal of AI Research"],
                    "DOI": "10.1234/ai.neural.2023",
                    "created": {"date-time": "2023-05-20T10:00:00Z"},
                    "license": [{"URL": "http://creativecommons.org/licenses/by/4.0/"}],
                    "URL": "https://doi.org/10.1234/ai.neural.2023",
                    "is-referenced-by-count": 42
                },
                {
                    "title": ["Another Paper"],
                    "author": [{"given": "Peter", "family": "Jones"}],
                    "container-title": ["Proceedings of Science"],
                    "DOI": "10.5678/sci.proc.2022",
                    "created": {"date-time": "2022-11-01T12:30:00Z"},
                    "license": [], # Empty license list
                    "URL": "https://doi.org/10.5678/sci.proc.2022",
                    "is-referenced-by-count": 5
                }
            ]
        }
    }

@pytest.fixture
def crossref_searcher_with_mailto(mock_cache_manager):
    """Provides a CrossrefSearcher instance with a mailto email."""
    with patch('research_finder.searchers.crossref.CROSSREF_MAILTO', 'test@example.com'):
        return CrossrefSearcher(cache_manager=mock_cache_manager)

@pytest.fixture
def crossref_searcher_no_mailto(mock_cache_manager):
    """Provides a CrossrefSearcher instance without a mailto email."""
    with patch('research_finder.searchers.crossref.CROSSREF_MAILTO', ''):
        return CrossrefSearcher(cache_manager=mock_cache_manager)

# --- Test Suite ---

class TestCrossrefSearcher:
    """Test suite for the CrossrefSearcher class."""

    def test_init_with_mailto_sets_correct_rate_limit(self, crossref_searcher_with_mailto):
        """Test that providing a mailto email sets the 'polite' rate limit."""
        assert crossref_searcher_with_mailto.name == "CrossRef"
        assert crossref_searcher_with_mailto.mailto == 'test@example.com'
        assert crossref_searcher_with_mailto.rate_limit == 1.0 # Assuming this is the polite limit

    def test_init_without_mailto_sets_correct_rate_limit(self, crossref_searcher_no_mailto):
        """Test that not providing a mailto email sets the 'unpolite' rate limit."""
        assert crossref_searcher_no_mailto.mailto == ''
        assert crossref_searcher_no_mailto.rate_limit == 2.0 # Assuming this is the unpolite limit

    @patch('research_finder.searchers.crossref.requests.get')
    def test_search_keyword_query_with_filters(self, mock_get, crossref_searcher_with_mailto, sample_crossref_api_response):
        """Test a keyword search with year filters and a mailto parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_crossref_api_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        filters = {'year_min': '2022', 'year_max': '2023'}
        crossref_searcher_with_mailto.search("neural networks", limit=5, search_type='keyword', filters=filters)

        # Assert the API was called with the correct parameters
        mock_get.assert_called_once()
        params = mock_get.call_args[1]['params']
        assert params['query'] == 'neural networks'
        assert params['rows'] == 5
        assert params['filter'] == 'from-pub-date:2022,until-pub-date:2023'
        assert params['mailto'] == 'test@example.com'

    @patch('research_finder.searchers.crossref.requests.get')
    def test_search_title_query(self, mock_get, crossref_searcher_with_mailto, sample_crossref_api_response):
        """Test a title-specific search."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_crossref_api_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crossref_searcher_with_mailto.search("neural networks", limit=10, search_type='title')

        params = mock_get.call_args[1]['params']
        assert params['query.title'] == 'neural networks'
        assert 'query' not in params

    @patch('research_finder.searchers.crossref.requests.get')
    def test_search_author_query(self, mock_get, crossref_searcher_with_mailto, sample_crossref_api_response):
        """Test an author-specific search."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_crossref_api_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crossref_searcher_with_mailto.search("John Doe", limit=10, search_type='author')

        params = mock_get.call_args[1]['params']
        assert params['query.author'] == 'John Doe'

    @patch('research_finder.searchers.crossref.requests.get')
    def test_search_parses_response_correctly(self, mock_get, crossref_searcher_with_mailto, sample_crossref_api_response):
        """Test that the API response is parsed into the correct paper format."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_crossref_api_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        crossref_searcher_with_mailto.search("neural networks", limit=10)
        
        assert len(crossref_searcher_with_mailto.results) == 2
        
        result1 = crossref_searcher_with_mailto.results[0]
        assert result1['Title'] == 'A Comprehensive Study on Neural Networks'
        assert result1['Authors'] == 'John Doe, Jane Smith, Unknown'
        assert result1['Year'] == '2023'
        assert result1['Venue'] == 'Journal of AI Research'
        assert result1['Source'] == 'CrossRef'
        assert result1['Citation Count'] == 42
        assert result1['DOI'] == '10.1234/ai.neural.2023'
        assert result1['License Type'] == 'http://creativecommons.org/licenses/by/4.0/'
        assert result1['URL'] == 'https://doi.org/10.1234/ai.neural.2023'

        result2 = crossref_searcher_with_mailto.results[1]
        assert result2['Title'] == 'Another Paper'
        assert result2['Authors'] == 'Peter Jones'
        assert result2['Year'] == '2022'
        assert result2['License Type'] == 'N/A' # Handles empty license list

    @patch('research_finder.searchers.crossref.requests.get')
    def test_search_applies_post_search_citation_filter(self, mock_get, crossref_searcher_with_mailto, sample_crossref_api_response):
        """Test that the min_citations filter is applied after fetching results."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_crossref_api_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        filters = {'min_citations': 20}
        crossref_searcher_with_mailto.search("neural networks", limit=10, filters=filters)

        # Only the first paper should be kept
        assert len(crossref_searcher_with_mailto.results) == 1
        assert crossref_searcher_with_mailto.results[0]['Title'] == 'A Comprehensive Study on Neural Networks'

    def test_search_uses_cache_on_hit(self, crossref_searcher_with_mailto, mock_cache_manager):
        """Test that the searcher returns cached results if they exist."""
        cached_data = [{'Title': 'Cached Paper'}]
        mock_cache_manager.get.return_value = cached_data

        crossref_searcher_with_mailto.search("test query", 10)

        mock_cache_manager.get.assert_called_once()
        with patch('research_finder.searchers.crossref.requests.get') as mock_get:
            crossref_searcher_with_mailto.search("test query", 10)
            mock_get.assert_not_called()
        assert crossref_searcher_with_mailto.results == cached_data

    @patch('research_finder.searchers.crossref.requests.get')
    def test_search_saves_to_cache_on_miss(self, mock_get, crossref_searcher_with_mailto, sample_crossref_api_response, mock_cache_manager):
        """Test that new results are saved to the cache after a successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_crossref_api_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        mock_cache_manager.get.return_value = None # Simulate cache miss

        # FIX: This line was commented out. It needs to be here.
        crossref_searcher_with_mailto.search("test query", 10)

        mock_cache_manager.set.assert_called_once()
        args, _ = mock_cache_manager.set.call_args
        # FIX: Changed args[1] to args[3]
        assert len(args[3]) == 2

    @patch('research_finder.searchers.crossref.requests.get')
    def test_search_handles_request_exception(self, mock_get, crossref_searcher_with_mailto, caplog):
        """Test that general request exceptions are caught and logged."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        crossref_searcher_with_mailto.search("bad query", 10)

        assert crossref_searcher_with_mailto.results == []
        assert "API request failed: Network error" in caplog.text

    @patch('research_finder.searchers.crossref.requests.get')
    def test_enforces_rate_limit(self, mock_get, crossref_searcher_with_mailto, sample_crossref_api_response):
        """Test that the searcher calls its rate limiting method."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_crossref_api_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(crossref_searcher_with_mailto, '_enforce_rate_limit') as mock_rate_limit:
            crossref_searcher_with_mailto.search("test query", 10)
            mock_rate_limit.assert_called_once()
