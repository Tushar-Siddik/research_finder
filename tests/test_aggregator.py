"""
Pytest-style tests for the aggregator.py module.

This test suite verifies the functionality of the Aggregator class, including
adding searchers, running searches, de-duplication logic, and handling
searcher failures gracefully.
"""

import pytest
import sys
from unittest.mock import MagicMock, patch

from research_finder.aggregator import Aggregator
from research_finder.searchers.base_searcher import BaseSearcher

# --- Mock Searcher for Testing ---

class MockSearcher(BaseSearcher):
    """A simple mock searcher for testing the Aggregator."""
    def __init__(self, name: str, results: list, should_fail: bool = False):
        super().__init__(name)
        self.results = results
        self.should_fail = should_fail
        self.search_called_with = None

    def search(self, query: str, limit: int, search_type: str, filters: dict):
        self.search_called_with = (query, limit, search_type, filters)
        if self.should_fail:
            raise RuntimeError(f"Mock searcher '{self.name}' failed!")
        self._results = self.results

    def get_results(self):
        return self._results

# --- Fixtures for Aggregator Tests ---

@pytest.fixture
def aggregator():
    """Provides an Aggregator instance for testing."""
    return Aggregator()

@pytest.fixture
def sample_results_1():
    """Sample results from the first mock searcher."""
    return [
        {'Title': 'AI and the Future', 'DOI': '10.1001/ai.future', 'Source': 'Source A'},
        {'Title': 'Quantum Computing Explained', 'DOI': '10.1002/quantum', 'Source': 'Source A'},
        {'Title': 'A Study on Python', 'DOI': '', 'Source': 'Source A'}, # No DOI
    ]

@pytest.fixture
def sample_results_2():
    """Sample results from the second mock searcher, with some overlaps."""
    return [
        {'Title': 'AI and the Future', 'DOI': '10.1001/ai.future', 'Source': 'Source B'}, # Duplicate by DOI
        {'Title': 'A Study on Python', 'DOI': '', 'Source': 'Source B'}, # Duplicate by Title
        {'Title': 'New Discoveries in Biology', 'DOI': '10.1003/bio', 'Source': 'Source B'},
    ]

@pytest.fixture
def mock_searcher_1(sample_results_1):
    """A successful mock searcher instance."""
    return MockSearcher(name="MockSearcher1", results=sample_results_1)

@pytest.fixture
def mock_searcher_2(sample_results_2):
    """Another successful mock searcher instance."""
    return MockSearcher(name="MockSearcher2", results=sample_results_2)

@pytest.fixture
def failing_searcher():
    """A mock searcher that will raise an exception."""
    return MockSearcher(name="FailingSearcher", results=[], should_fail=True)


# --- Test Suite ---

class TestAggregator:
    """Test suite for the Aggregator class."""

    def test_init(self, aggregator):
        """Test that the Aggregator initializes correctly."""
        assert aggregator.searchers == []
        assert aggregator.last_successful_searchers == []
        assert aggregator.last_failed_searchers == []
        assert aggregator.cache_manager is not None

    def test_add_searcher_success(self, aggregator, mock_searcher_1):
        """Test adding a valid searcher."""
        aggregator.add_searcher(mock_searcher_1)
        assert len(aggregator.searchers) == 1
        assert aggregator.searchers[0] == mock_searcher_1
        # Check that the cache manager was passed to the searcher
        assert mock_searcher_1.cache_manager == aggregator.cache_manager

    def test_add_searcher_failure(self, aggregator):
        """Test that adding an invalid object is logged and does not add it."""
        invalid_searcher = "not a searcher"
        with patch.object(aggregator.logger, 'error') as mock_log:
            aggregator.add_searcher(invalid_searcher)
            assert len(aggregator.searchers) == 0
            mock_log.assert_called_once()

    def test_run_all_searches_deduplication(self, aggregator, mock_searcher_1, mock_searcher_2):
        """Test that de-duplication works correctly for both DOI and title."""
        aggregator.add_searcher(mock_searcher_1)
        aggregator.add_searcher(mock_searcher_2)
        
        results = aggregator.run_all_searches("test query", 10)
        
        # Expected unique results: AI, Quantum, Python, Bio
        assert len(results) == 4
        
        titles = {r['Title'] for r in results}
        assert titles == {
            'AI and the Future', 
            'Quantum Computing Explained', 
            'A Study on Python', 
            'New Discoveries in Biology'
        }
        
        # Check that the unique result is from the first source seen
        python_result = next(r for r in results if r['Title'] == 'A Study on Python')
        assert python_result['Source'] == 'Source A'

    def test_run_all_searches_stream(self, aggregator, mock_searcher_1, mock_searcher_2):
        """Test that streaming returns a generator and yields correct results."""
        aggregator.add_searcher(mock_searcher_1)
        aggregator.add_searcher(mock_searcher_2)
        
        results_stream = aggregator.run_all_searches("test query", 10, stream=True)
        
        # It should be a generator, not a list
        assert hasattr(results_stream, '__iter__')
        assert not hasattr(results_stream, '__len__')
        
        # Consume the generator and check results
        results_list = list(results_stream)
        assert len(results_list) == 4

    def test_run_all_searches_handles_searcher_failure(self, aggregator, mock_searcher_1, failing_searcher):
        """Test that the aggregator continues even if one searcher fails."""
        aggregator.add_searcher(mock_searcher_1)
        aggregator.add_searcher(failing_searcher)
        
        with patch.object(aggregator.logger, 'error') as mock_log:
            results = aggregator.run_all_searches("test query", 10)
            
            # Should still get results from the successful searcher
            assert len(results) == 3
            
            # Check the summary
            summary = aggregator.get_last_run_summary()
            assert 'MockSearcher1' in summary['successful']
            assert 'FailingSearcher' in summary['failed']
            
            # Check that the error was logged
            mock_log.assert_called_once()
            assert "An error occurred with searcher 'FailingSearcher'" in mock_log.call_args[0][0]

    def test_get_last_run_summary(self, aggregator, mock_searcher_1, failing_searcher):
        """Test the summary report after a run."""
        aggregator.add_searcher(mock_searcher_1)
        aggregator.add_searcher(failing_searcher)
        
        aggregator.run_all_searches("test query", 10)
        
        summary = aggregator.get_last_run_summary()
        assert summary['successful'] == ['MockSearcher1']
        assert summary['failed'] == ['FailingSearcher']

    def test_clear_cache_delegates_to_manager(self, aggregator):
        """Test that clear_cache calls the cache manager's clear method."""
        with patch.object(aggregator.cache_manager, 'clear') as mock_clear:
            aggregator.clear_cache()
            mock_clear.assert_called_once()

    def test_clear_expired_cache_delegates_to_manager(self, aggregator):
        """Test that clear_expired_cache calls the cache manager's clear_expired method."""
        with patch.object(aggregator.cache_manager, 'clear_expired') as mock_clear_expired:
            aggregator.clear_expired_cache()
            mock_clear_expired.assert_called_once()

    @patch('research_finder.aggregator.tqdm')
    def test_progress_bar_is_used(self, mock_tqdm, aggregator, mock_searcher_1):
        """Test that tqdm is used to wrap the searchers and update the progress bar."""
        # Create a mock that will act as the tqdm progress bar
        mock_pbar = MagicMock()
        # Make the mock iterable, so it can be used in a for loop
        mock_pbar.__iter__ = MagicMock(return_value=iter([mock_searcher_1]))
        
        # Configure the patched tqdm to return our mock progress bar
        mock_tqdm.return_value = mock_pbar
        
        aggregator.add_searcher(mock_searcher_1)
        aggregator.run_all_searches("test query", 10)
        
        # Assert that tqdm was called with the correct arguments
        mock_tqdm.assert_called_once_with(
            [mock_searcher_1], 
            desc="Searching Vendors", 
            unit="source", 
            file=sys.stdout
        )
        
        # Assert that the progress bar's text was updated
        mock_pbar.set_postfix_str.assert_called_with("Current: MockSearcher1")
