"""
Pytest-style tests for the google_scholar.py searcher module.

This test suite verifies the functionality of the GoogleScholarSearcher class.
Due to the nature of scraping Google Scholar, these tests are skipped by default
to avoid triggering CAPTCHAs. They can be run manually for debugging.
"""

import pytest
from unittest.mock import MagicMock, patch

from research_finder.searchers.google_scholar import GoogleScholarSearcher

# --- Mock Data for Scholarly Library ---

@pytest.fixture
def mock_scholarly_pub_1():
    """A mock publication dictionary from the scholarly library."""
    return {
        'bib': {
            'title': '  The Transformer Architecture  ',
            'author': 'Vaswani, A. and Shazeer, N.',
            'pub_year': '2017',
            'num_citations': '50000',
            'journal': 'NeurIPS'
        },
        'pub_url': 'https://doi.org/10.1001/nips.2017.123456'
    }

@pytest.fixture
def mock_scholarly_pub_2():
    """A second mock publication, designed to be filtered out."""
    return {
        'bib': {
            'title': 'An Old Paper',
            'author': 'Smith, J.',
            'pub_year': '1995',
            'num_citations': '150',
            'journal': 'Old Science Journal'
        },
        'pub_url': 'https://example.com/paper/old' # No DOI
    }

@pytest.fixture
def mock_scholarly_generator(mock_scholarly_pub_1, mock_scholarly_pub_2):
    """A mock generator that yields publications from scholarly.search_pubs."""
    def gen():
        yield mock_scholarly_pub_1
        yield mock_scholarly_pub_2
    return gen()


# The skip marker is applied to the entire class.
@pytest.mark.skip(reason="Google Scholar tests can trigger CAPTCHAs and are unreliable for CI.")
class TestGoogleScholarSearcher:
    """Test suite for the GoogleScholarSearcher class."""

    def test_init_raises_import_error_if_scholarly_missing(self, mock_cache_manager):
        """Test that initialization fails if the scholarly library is not installed."""
        with patch('research_finder.searchers.google_scholar.scholarly', None):
            with pytest.raises(ImportError, match="scholarly library not found"):
                GoogleScholarSearcher(cache_manager=mock_cache_manager)

    def test_init_sets_rate_limit_and_logs_warning(self, mock_cache_manager, caplog):
        """Test that the searcher initializes with the correct rate limit and a warning."""
        searcher = GoogleScholarSearcher(cache_manager=mock_cache_manager)
        assert searcher.name == "Google Scholar"
        assert searcher.rate_limit == 5.0 # From config
        assert "Rate limiting is critical to avoid being blocked" in caplog.text

    def test_search_uses_cache_on_hit(self, mock_cache_manager):
        """Test that the searcher returns cached results if they exist."""
        cached_data = [{'Title': 'Cached Paper'}]
        mock_cache_manager.get.return_value = cached_data
        
        searcher = GoogleScholarSearcher(cache_manager=mock_cache_manager)
        searcher.search("test query", 10)

        mock_cache_manager.get.assert_called_once()
        with patch('research_finder.searchers.google_scholar.scholarly.search_pubs') as mock_search:
            searcher.search("test query", 10)
            mock_search.assert_not_called()
        assert searcher.results == cached_data

    @patch('research_finder.searchers.google_scholar.scholarly.search_pubs')
    def test_search_keyword_query_and_parsing(self, mock_search_pubs, mock_cache_manager, mock_scholarly_generator):
        """Test a standard keyword search and data parsing."""
        mock_search_pubs.return_value = mock_scholarly_generator()
        
        searcher = GoogleScholarSearcher(cache_manager=mock_cache_manager)
        with patch.object(searcher, '_enforce_rate_limit') as mock_rate_limit:
            searcher.search("transformer architecture", limit=5)

        # Assert the correct query was used
        mock_search_pubs.assert_called_once_with("transformer architecture")
        
        # Assert rate limit was called for each item fetched
        assert mock_rate_limit.call_count == 2

        # Assert results were parsed and stored correctly
        assert len(searcher.results) == 2
        result1 = searcher.results[0]
        assert result1['Title'] == 'The Transformer Architecture'
        assert result1['Authors'] == 'Vaswani, A. and Shazeer, N.'
        assert result1['Year'] == '2017'
        assert result1['Venue'] == 'NeurIPS'
        assert result1['Source'] == 'Google Scholar'
        assert result1['Citation Count'] == 50000
        assert result1['DOI'] == '10.1001/nips.2017.123456'
        assert result1['License Type'] == 'N/A'

    @patch('research_finder.searchers.google_scholar.scholarly.search_pubs')
    def test_search_title_and_author_queries(self, mock_search_pubs, mock_cache_manager, mock_scholarly_generator):
        """Test that title and author search terms are constructed correctly."""
        mock_search_pubs.return_value = mock_scholarly_generator()
        searcher = GoogleScholarSearcher(cache_manager=mock_cache_manager)

        # Test title search
        searcher.search("transformer architecture", search_type='title')
        assert mock_search_pubs.call_args[0][0] == '"transformer architecture"'

        # Reset the mock for the next test
        mock_search_pubs.reset_mock()
        mock_search_pubs.return_value = mock_scholarly_generator()
        
        # Test author search
        searcher.search("Vaswani", search_type='author')
        assert mock_search_pubs.call_args[0][0] == "author:Vaswani"

    @patch('research_finder.searchers.google_scholar.scholarly.search_pubs')
    def test_search_applies_post_search_filters(self, mock_search_pubs, mock_cache_manager, mock_scholarly_generator):
        """Test that year and citation filters are applied correctly after fetching."""
        mock_search_pubs.return_value = mock_scholarly_generator()
        searcher = GoogleScholarSearcher(cache_manager=mock_cache_manager)

        # Filter for papers after 2000
        filters = {'year_min': '2000'}
        searcher.search("query", limit=10, filters=filters)

        # Only the first paper should be kept
        assert len(searcher.results) == 1
        assert searcher.results[0]['Title'] == 'The Transformer Architecture'
        
        # Reset for next test
        mock_search_pubs.reset_mock()
        mock_search_pubs.return_value = mock_scholarly_generator()
        searcher.results = []
        
        # Filter for papers with more than 1000 citations
        filters = {'min_citations': 1000}
        searcher.search("query", limit=10, filters=filters)
        
        # Only the first paper should be kept
        assert len(searcher.results) == 1
        assert searcher.results[0]['Title'] == 'The Transformer Architecture'

    @patch('research_finder.searchers.google_scholar.scholarly.search_pubs')
    def test_search_handles_exception_gracefully(self, mock_search_pubs, mock_cache_manager, caplog):
        """Test that exceptions during the search are caught and logged."""
        mock_search_pubs.side_effect = Exception("Scraping failed")
        searcher = GoogleScholarSearcher(cache_manager=mock_cache_manager)

        searcher.search("query", limit=10)

        assert searcher.results == []
        assert "Search failed: Scraping failed. This is common with Google Scholar." in caplog.text