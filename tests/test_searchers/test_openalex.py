"""
Pytest-style tests for the openalex.py searcher module.

This test suite verifies the functionality of the OpenAlexSearcher class, including
initialization with and without an email, query construction using the pyalex
library, API response parsing, filtering, caching, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from research_finder.searchers.openalex import OpenAlexSearcher, PYALEX_AVAILABLE

# --- Mock Data for OpenAlex API Response ---

@pytest.fixture
def sample_openalex_work():
    """A mock dictionary representing a single work from the OpenAlex API."""
    return {
        'id': 'https://openalex.org/W123456789',
        'display_name': '  A Novel Approach to Quantum Entanglement  ',
        'publication_year': 2022,
        'cited_by_count': 150,
        'doi': '10.5555/quantum.ent.2022',
        'type': 'journal-article',
        'primary_location': {
            'source': {
                'display_name': 'Journal of Quantum Physics'
            }
        },
        'authorships': [
            {'author': {'display_name': 'Alice Smith'}},
            {'author': {'display_name': 'Bob Johnson'}},
            {'author': {'display_name': '  Charlie Brown  '}}
        ],
        'best_oa_location': {
            'license': 'https://creativecommons.org/licenses/by/4.0/'
        }
    }

@pytest.fixture
def openalex_searcher_with_email(mock_cache_manager):
    """Provides an OpenAlexSearcher instance with an email configured."""
    with patch('research_finder.searchers.openalex.OPENALEX_EMAIL', 'test@example.com'):
        return OpenAlexSearcher(cache_manager=mock_cache_manager)

@pytest.fixture
def openalex_searcher_no_email(mock_cache_manager):
    """Provides an OpenAlexSearcher instance without an email configured."""
    # FIX: Use a different approach to test without email
    # Instead of patching the config, we'll create a new instance with a different config
    with patch('research_finder.searchers.openalex.OPENALEX_EMAIL', ''):
        with patch('research_finder.searchers.openalex.pyalex') as mock_pyalex:
            mock_config = MagicMock()
            mock_config.email = ''
            mock_pyalex.config = mock_config
            return OpenAlexSearcher(cache_manager=mock_cache_manager)

# --- Test Suite ---

class TestOpenAlexSearcher:
    """Test suite for the OpenAlexSearcher class."""

    def test_init_raises_import_error_if_pyalex_missing(self, mock_cache_manager):
        """Test that initialization fails if pyalex is not installed."""
        with patch('research_finder.searchers.openalex.PYALEX_AVAILABLE', False):
            with pytest.raises(ImportError, match="pyalex package not found"):
                OpenAlexSearcher(cache_manager=mock_cache_manager)

    def test_init_with_email_sets_rate_limit(self, openalex_searcher_with_email):
        """Test that providing an email sets the 'polite' rate limit and configures pyalex."""
        assert openalex_searcher_with_email.name == "OpenAlex"
        assert openalex_searcher_with_email.rate_limit == 0.1 # Polite limit
        # Check that pyalex.config was set
        from research_finder.searchers import openalex as openalex_module
        assert openalex_module.pyalex.config.email == 'test@example.com'

    def test_init_without_email_sets_rate_limit(self, openalex_searcher_no_email):
        """Test that not providing an email sets the 'unpolite' rate limit."""
        assert openalex_searcher_no_email.rate_limit == 0.5 # Unpolite limit
        # We don't need to check the email config since we're mocking it

    @patch('research_finder.searchers.openalex.Works')
    def test_search_keyword_query(self, mock_works, openalex_searcher_with_email, sample_openalex_work):
        """Test a standard keyword search and data parsing."""
        # Mock the fluent interface of pyalex
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        mock_query.search.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.get.return_value = [sample_openalex_work]

        openalex_searcher_with_email.search("quantum entanglement", limit=10)

        # Assert the query was built correctly
        mock_works.assert_called_once()
        mock_query.search.assert_called_once_with("quantum entanglement")
        mock_query.get.assert_called_once_with(per_page=10)

        # Assert the results were parsed and stored correctly
        assert len(openalex_searcher_with_email.results) == 1
        result = openalex_searcher_with_email.results[0]
        assert result['Title'] == 'A Novel Approach to Quantum Entanglement'
        assert result['Authors'] == 'Alice Smith, Bob Johnson, Charlie Brown'
        assert result['Year'] == '2022'
        assert result['Venue'] == 'Journal of Quantum Physics'
        assert result['Source'] == 'OpenAlex'
        assert result['Citation Count'] == 150
        assert result['DOI'] == '10.5555/quantum.ent.2022'
        assert result['License Type'] == 'https://creativecommons.org/licenses/by/4.0/'
        assert result['URL'] == 'https://openalex.org/W123456789'

    @patch('research_finder.searchers.openalex.Works')
    def test_search_title_query(self, mock_works, openalex_searcher_with_email, sample_openalex_work):
        """Test a title-specific search."""
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.get.return_value = [sample_openalex_work]

        openalex_searcher_with_email.search("quantum entanglement", search_type='title')

        # Assert the correct filter was applied
        mock_query.filter.assert_called_with(title={"search": "quantum entanglement"})

    @patch('research_finder.searchers.openalex.Works')
    def test_search_author_query(self, mock_works, openalex_searcher_with_email, sample_openalex_work):
        """Test an author-specific search."""
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.get.return_value = [sample_openalex_work]

        openalex_searcher_with_email.search("Alice Smith", search_type='author')

        # Assert the correct filter was applied
        mock_query.filter.assert_called_with(author={"display_name": "Alice Smith"})

    @patch('research_finder.searchers.openalex.Works')
    def test_search_with_filters(self, mock_works, openalex_searcher_with_email, sample_openalex_work):
        """Test that year and citation filters are applied correctly."""
        # FIX: Set up the mock to properly track filter calls
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        
        # Make sure filter returns the mock_query itself for chaining
        mock_query.filter.return_value = mock_query
        mock_query.search.return_value = mock_query
        mock_query.get.return_value = [sample_openalex_work]

        filters = {'year_min': '2020', 'year_max': '2023', 'min_citations': 100}
        openalex_searcher_with_email.search("quantum", filters=filters)

        # FIX: Check that filter was called with the correct arguments
        # We need to check all calls to filter, not just the last one
        assert mock_query.filter.call_count == 2
        # Check the first call for year filter
        mock_query.filter.assert_any_call(publication_year={">=": '2020', "<=": '2023'})
        # Check the second call for citation filter
        mock_query.filter.assert_any_call(cited_by_count={">=": 100})

    @patch('research_finder.searchers.openalex.Works')
    def test_search_handles_no_results(self, mock_works, openalex_searcher_with_email):
        """Test that an empty result set from the API is handled correctly."""
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        mock_query.search.return_value = mock_query
        mock_query.get.return_value = [] # No results

        openalex_searcher_with_email.search("nonexistent query")

        assert openalex_searcher_with_email.results == []

    def test_search_uses_cache_on_hit(self, openalex_searcher_with_email, mock_cache_manager):
        """Test that the searcher returns cached results if they exist."""
        cached_data = [{'Title': 'Cached Paper'}]
        mock_cache_manager.get.return_value = cached_data

        openalex_searcher_with_email.search("test query", 10)

        mock_cache_manager.get.assert_called_once()
        with patch('research_finder.searchers.openalex.Works') as mock_works:
            openalex_searcher_with_email.search("test query", 10)
            mock_works.assert_not_called()
        assert openalex_searcher_with_email.results == cached_data

    @patch('research_finder.searchers.openalex.Works')
    def test_search_saves_to_cache_on_miss(
        self, 
        mock_works,  # Keep this mock
        openalex_searcher_with_email,  # Use the correct searcher fixture
        sample_openalex_work,           # Use the correct data fixture
        mock_cache_manager
    ):
        """Test that new results are saved to the cache after a successful API call."""
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        mock_query.search.return_value = mock_query
        mock_query.get.return_value = [sample_openalex_work]
        mock_cache_manager.get.return_value = None

        openalex_searcher_with_email.search("test query", 10)

        mock_cache_manager.set.assert_called_once()
        args, _ = mock_cache_manager.set.call_args
        # FIX: Changed args[1] to args[3]
        assert len(args[3]) == 1

    @patch('research_finder.searchers.openalex.Works')
    def test_search_handles_exception(self, mock_works, openalex_searcher_with_email, caplog):
        """Test that exceptions during the search are caught and logged."""
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        mock_query.search.return_value = mock_query
        mock_query.get.side_effect = ValueError("An unexpected error from pyalex")

        openalex_searcher_with_email.search("bad query", 10)

        assert openalex_searcher_with_email.results == []
        assert "An error occurred with OpenAlex search: An unexpected error from pyalex" in caplog.text

    @patch('research_finder.searchers.openalex.Works')
    def test_enforces_rate_limit(self, mock_works, openalex_searcher_with_email, sample_openalex_work):
        """Test that the searcher calls its rate limiting method."""
        mock_query = MagicMock()
        mock_works.return_value.select.return_value = mock_query
        mock_query.search.return_value = mock_query
        mock_query.get.return_value = [sample_openalex_work]

        with patch.object(openalex_searcher_with_email, '_enforce_rate_limit') as mock_rate_limit:
            openalex_searcher_with_email.search("test query", 10)
            mock_rate_limit.assert_called_once()