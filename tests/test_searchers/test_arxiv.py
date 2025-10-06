"""
Pytest-style tests for the arxiv.py searcher module.

This test suite verifies the functionality of the ArxivSearcher class, including
query construction, API response parsing, data transformation, caching,
and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from research_finder.searchers.arxiv import ArxivSearcher
import requests.exceptions

# --- Mock Data for arXiv Feedparser Response ---

@pytest.fixture
def sample_arxiv_feed():
    """A mock object that simulates the structure of a feedparser parsed arXiv feed."""
    mock_feed = MagicMock()
    
    # Create two mock entries to test parsing multiple results
    entry1 = MagicMock()
    entry1.title = "  A Study on Machine Learning: A New Approach  " # Title with extra spaces
    entry1.id = "http://arxiv.org/abs/2301.01234v1"
    entry1.published = "2023-01-05T12:00:00Z"
    entry1.link = "http://arxiv.org/abs/2301.01234v1"
    entry1.rights = "cc-by-4.0"
    # Configure the get method to return the correct value for 'rights'
    entry1.get = lambda key, default=None: entry1.rights if key == 'rights' else default
    
    # Properly configure mock authors with name attributes
    author1 = MagicMock()
    author1.name = "John Doe"
    author2 = MagicMock()
    author2.name = " Jane Smith "
    entry1.authors = [author1, author2]

    entry2 = MagicMock()
    entry2.title = "Quantum Computing for Beginners"
    entry2.id = "http://arxiv.org/abs/2212.05678v2" # A different ID format
    entry2.published = "2022-12-15T10:30:00Z"
    entry2.link = "http://arxiv.org/abs/2212.05678v2"
    entry2.rights = None # Test missing rights
    # Configure the get method to return the correct value for 'rights'
    entry2.get = lambda key, default=None: entry2.rights if key == 'rights' else default
    
    # Properly configure mock author with name attribute
    author3 = MagicMock()
    author3.name = "Peter Jones"
    entry2.authors = [author3]

    mock_feed.entries = [entry1, entry2]
    return mock_feed

@pytest.fixture
def arxiv_searcher(mock_cache_manager):
    """Provides an ArxivSearcher instance with a mock cache manager."""
    return ArxivSearcher(cache_manager=mock_cache_manager)

# --- Test Suite ---

class TestArxivSearcher:
    """Test suite for the ArxivSearcher class."""

    def test_init(self, arxiv_searcher):
        """Test that the ArxivSearcher initializes correctly."""
        assert arxiv_searcher.name == "arXiv"
        assert arxiv_searcher.rate_limit > 0
        assert arxiv_searcher.cache_manager is not None

    @patch('research_finder.searchers.arxiv.feedparser.parse')
    @patch('research_finder.searchers.arxiv.requests.get')
    def test_search_keyword_query(self, mock_get, mock_parse, arxiv_searcher, sample_arxiv_feed):
        """Test a standard keyword search and data parsing."""
        mock_response = MagicMock(content=b"some xml data")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        mock_parse.return_value = sample_arxiv_feed

        arxiv_searcher.search("machine learning", limit=5)

        # Verify API call and parsing
        mock_get.assert_called_once()
        mock_parse.assert_called_once_with(b"some xml data")
        params = mock_get.call_args[1]['params']
        assert params['search_query'] == 'all:"machine learning"'
        assert params['max_results'] == 5

        # Verify results were parsed and stored correctly
        assert len(arxiv_searcher.results) == 2
        result1 = arxiv_searcher.results[0]
        assert result1['Title'] == 'A Study on Machine Learning: A New Approach'
        assert result1['Authors'] == 'John Doe, Jane Smith'
        assert result1['Year'] == '2023'
        assert result1['Source'] == 'arXiv'
        assert result1['Venue'] == 'arXiv'
        assert result1['DOI'] == '10.48550/arXiv.2301.01234v1'
        assert result1['License Type'] == 'cc-by-4.0'
        
        result2 = arxiv_searcher.results[1]
        # FIX: Corrected assertion to match normalize_string output
        assert result2['Title'] == 'Quantum Computing for Beginners'
        assert result2['DOI'] == '10.48550/arXiv.2212.05678v2'
        assert result2['License Type'] == 'N/A' # Handles missing rights

    @patch('research_finder.searchers.arxiv.feedparser.parse')
    @patch('research_finder.searchers.arxiv.requests.get')
    def test_search_title_query(self, mock_get, mock_parse, arxiv_searcher, sample_arxiv_feed):
        """Test a title-specific search."""
        mock_get.return_value = MagicMock()
        mock_parse.return_value = sample_arxiv_feed

        arxiv_searcher.search("machine learning", limit=10, search_type='title')
        params = mock_get.call_args[1]['params']
        assert params['search_query'] == 'ti:"machine learning"'

    @patch('research_finder.searchers.arxiv.feedparser.parse')
    @patch('research_finder.searchers.arxiv.requests.get')
    def test_search_author_query(self, mock_get, mock_parse, arxiv_searcher, sample_arxiv_feed):
        """Test an author-specific search."""
        mock_get.return_value = MagicMock()
        mock_parse.return_value = sample_arxiv_feed

        arxiv_searcher.search("John Doe", limit=10, search_type='author')
        params = mock_get.call_args[1]['params']
        assert params['search_query'] == 'au:"John Doe"'

    def test_search_uses_cache_on_hit(self, arxiv_searcher, mock_cache_manager):
        """Test that the searcher returns cached results if they exist."""
        cached_data = [{'Title': 'Cached Paper'}]
        mock_cache_manager.get.return_value = cached_data

        arxiv_searcher.search("test query", 10)

        mock_cache_manager.get.assert_called_once()
        with patch('research_finder.searchers.arxiv.requests.get') as mock_get:
            arxiv_searcher.search("test query", 10)
            mock_get.assert_not_called()
        assert arxiv_searcher.results == cached_data

    @patch('research_finder.searchers.arxiv.feedparser.parse')
    @patch('research_finder.searchers.arxiv.requests.get')
    def test_search_saves_to_cache_on_miss(self, mock_get, mock_parse, arxiv_searcher, sample_arxiv_feed, mock_cache_manager):
        """Test that new results are saved to the cache after a successful API call."""
        mock_get.return_value = MagicMock()
        mock_parse.return_value = sample_arxiv_feed
        mock_cache_manager.get.return_value = None # Simulate cache miss

        arxiv_searcher.search("test query", 10)

        mock_cache_manager.set.assert_called_once()
        args, _ = mock_cache_manager.set.call_args
        assert len(args[3]) == 2 # The results list

    @patch('research_finder.searchers.arxiv.feedparser.parse')
    @patch('research_finder.searchers.arxiv.requests.get')
    def test_search_handles_http_error(self, mock_get, mock_parse, arxiv_searcher, caplog):
        """Test that HTTP errors are caught and logged gracefully."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        arxiv_searcher.search("bad query", 10)

        assert arxiv_searcher.results == []
        assert "HTTP error occurred: 404 Not Found" in caplog.text

    @patch('research_finder.searchers.arxiv.requests.get')
    def test_search_handles_timeout(self, mock_get, arxiv_searcher, caplog):
        """Test that request timeouts are caught and logged gracefully."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        arxiv_searcher.search("slow query", 10)

        assert arxiv_searcher.results == []
        assert "Request to arXiv API timed out" in caplog.text

    @patch('research_finder.searchers.arxiv.feedparser.parse')
    @patch('research_finder.searchers.arxiv.requests.get')
    def test_enforces_rate_limit(self, mock_get, mock_parse, arxiv_searcher, sample_arxiv_feed):
        """Test that the searcher calls its rate limiting method."""
        mock_get.return_value = MagicMock()
        mock_parse.return_value = sample_arxiv_feed
        
        with patch.object(arxiv_searcher, '_enforce_rate_limit') as mock_rate_limit:
            arxiv_searcher.search("test query", 10)
            mock_rate_limit.assert_called_once()