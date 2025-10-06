"""
Shared fixtures and helper functions for the test suite.

This file is automatically discovered by pytest and provides utilities
like mocking environment variables, creating temporary data, and providing
sample data objects, which are commonly needed across different test files.
"""

import pytest
from unittest.mock import MagicMock
import importlib
from pathlib import Path
import config
import copy

# This is a reference to the module we will be testing.
# It's good practice to import it here so it can be reloaded.
CONFIG_MODULE = config


# =============================================================================
# Configuration and Environment Fixtures
# =============================================================================

# This is a reference to the module we will be testing.
# It's good practice to import it here so it can be reloaded.
CONFIG_MODULE = config

@pytest.fixture
def reload_config():
    """
    A helper function to reload the config module.

    The config module loads its values at import time. To test how it
    behaves with different environment variables, we need to reload it
    after changing the environment. This fixture returns a function
    that performs the reload.
    """
    def _reload():
        """The actual reload function."""
        return importlib.reload(CONFIG_MODULE)
    
    # FIX: Return the helper function, not the result of the reload.
    return _reload


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    A fixture to set environment variables for a test.

    It uses pytest's `monkeypatch` fixture to safely set environment
    variables, which are automatically restored after the test finishes.

    Usage:
    def test_something(mock_env_vars):
        mock_env_vars({"API_KEY": "test_key", "LOG_LEVEL": "DEBUG"})
        # ... your test logic here ...
    """
    def _set_env_vars(env_dict):
        for key, value in env_dict.items():
            monkeypatch.setenv(key, value)
    return _set_env_vars


@pytest.fixture
def temp_config_dirs(tmp_path, monkeypatch):
    """
    A fixture that overrides the cache and output directories to point
    to a temporary location for the duration of a test.

    This prevents tests from creating files in the actual project directories.
    It uses pytest's built-in `tmp_path` fixture, which handles cleanup.
    """
    # Create subdirectories in the temporary path
    temp_cache = tmp_path / "cache"
    temp_output = tmp_path / "output"
    temp_cache.mkdir()
    temp_output.mkdir()

    # Patch the config module's attributes to point to the temp dirs
    monkeypatch.setattr(CONFIG_MODULE, "CACHE_DIR", str(temp_cache))
    monkeypatch.setattr(CONFIG_MODULE, "DEFAULT_OUTPUT_DIR", str(temp_output))

    # The test runs here. We can yield the path if needed.
    yield tmp_path
    # Cleanup is handled automatically by pytest's tmp_path fixture.


# =============================================================================
# Author Data Fixtures
# =============================================================================

@pytest.fixture
def sample_authors_list_dict():
    """Provides a list of author dictionaries, as from Semantic Scholar."""
    return [
        {'name': 'John Doe'},
        {'name': 'Jane Smith'},
        {'name': '  Peter Jones  '}, # With extra whitespace
        {'name': ''}, # Empty name
        {'other_key': 'value'} # Missing 'name' key
    ]

@pytest.fixture
def sample_authors_list_string():
    """Provides a list of author strings, as from arXiv or CrossRef."""
    return [
        'John Doe',
        'Jane Smith',
        '  Peter Jones  ', # With extra whitespace
        '', # Empty string
        'Another Author'
    ]

@pytest.fixture
def sample_authors_string_comma():
    """Provides a comma-separated string of authors, as from Google Scholar."""
    return "John Doe, Jane Smith,  Peter Jones  , , Another Author"

@pytest.fixture
def many_authors_list():
    """Provides a list of 22 authors to test the >20 authors rule."""
    return [f'Author {i}' for i in range(1, 23)]


# =============================================================================
# Paper Data Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def _base_sample_paper():
    """A private, session-scoped base paper dictionary to avoid test pollution."""
    return {
        'Title': 'A Study on the Application of Unit Tests',
        'Authors': 'Doe, J., Smith, J.',
        'Year': '2023',
        'Venue': 'Journal of Software Testing, 15(2), 123-145',
        'Source': 'Semantic Scholar',
        'Citation Count': 5,
        'DOI': '10.1234/test.2023.123',
        'License Type': 'CC-BY',
        'URL': 'https://example.com/paper/123'
    }

@pytest.fixture
def sample_paper(_base_sample_paper):
    """
    A single, well-formed paper dictionary for testing.
    Returns a deep copy to prevent test pollution from functions that modify dicts in-place.
    """
    # FIX: Use copy.deepcopy to prevent modifications from leaking to other tests.
    return copy.deepcopy(_base_sample_paper)

@pytest.fixture
def sample_data_list(_base_sample_paper):
    """
    A list of two paper dictionaries for testing multi-record exports.
    Returns deep copies to prevent test pollution.
    """
    paper1 = copy.deepcopy(_base_sample_paper)
    paper2 = copy.deepcopy(_base_sample_paper)
    paper2['Title'] = 'Another Study on Software'
    paper2['Authors'] = 'Jones, P.'
    paper2['Year'] = '2022'
    return [paper1, paper2]

# @pytest.fixture
# def sample_data_generator(sample_data_list):
#     """A generator that yields papers, for testing streaming exports."""
#     for paper in sample_data_list:
#         yield paper

@pytest.fixture
def sample_data_generator(sample_data_list):
    """A generator that yields papers, for testing streaming exports."""
    # FIX: Use a generator expression to avoid teardown issues.
    return (paper for paper in sample_data_list)

# NOTE: The following fixtures were removed as they were redundant or less complete.
# - 'sample_paper_dict': Removed in favor of the more complete 'sample_paper' fixture.
#   Any tests using it should be updated to use 'sample_paper'.
# - 'sample_paper_dict_missing_data': Can be created within a test if needed, as it's a specific case.
# - 'sample_paper_dict_url_doi': Can be created within a test if needed.


# =============================================================================
# Mocking Fixtures
# =============================================================================

@pytest.fixture
def mock_cache_manager():
    """
    A mock cache manager to be used by searcher tests.
    By default, it simulates a cache miss.
    """
    mock_manager = MagicMock()
    mock_manager.get.return_value = None
    return mock_manager