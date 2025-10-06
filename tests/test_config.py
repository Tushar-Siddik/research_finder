# test_config.py
"""
Pytest-style tests for the config.py module.

This test suite verifies that configuration values are loaded correctly from
environment variables and that default values are applied when variables are not set.
It also checks the integrity of static configuration settings and path constructions.
"""

import pytest
from pathlib import Path
import config

# --- Tests for Static and Default Values ---

def test_project_root_is_absolute_path():
    """Test that PROJECT_ROOT is an absolute Path object."""
    assert isinstance(config.PROJECT_ROOT, Path)
    assert config.PROJECT_ROOT.is_absolute()

def test_static_api_urls_and_limits():
    """Test that static API URLs and rate limits have the correct values and types."""
    # Semantic Scholar
    assert config.SEMANTIC_SCHOLAR_API_URL == "https://api.semanticscholar.org/graph/v1/paper/search"
    assert config.SEMANTIC_SCHOLAR_RATE_LIMIT_WITH_KEY == 1.0
    assert isinstance(config.SEMANTIC_SCHOLAR_RATE_LIMIT_WITH_KEY, float)

    # arXiv
    assert config.ARXIV_API_URL == "http://export.arxiv.org/api/query"
    assert config.ARXIV_RATE_LIMIT == 0.5

    # ... you can add more checks for other static values here ...

def test_default_application_settings():
    """Test that default application settings are correct."""
    assert config.DEFAULT_RESULTS_LIMIT == 10
    assert config.REQUEST_TIMEOUT == 10
    assert config.CACHE_EXPIRY_HOURS == 24
    assert isinstance(config.DEFAULT_RESULTS_LIMIT, int)

def test_directory_settings(temp_config_dirs):
    """
    Test that directory settings are constructed correctly and can be
    overridden by the temp_config_dirs fixture.
    """
    # The fixture has already patched the config module
    assert config.CACHE_DIR.endswith("cache")
    assert config.DEFAULT_OUTPUT_DIR.endswith("output")
    
    # Verify they are inside the temp path provided by the fixture
    assert Path(config.CACHE_DIR).parent == temp_config_dirs
    assert Path(config.DEFAULT_OUTPUT_DIR).parent == temp_config_dirs

def test_logging_settings():
    """Test that logging settings have the correct values."""
    assert config.LOG_LEVEL == "INFO"
    assert config.LOG_FORMAT == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# --- Tests for Environment Variables using Fixtures ---

def test_api_keys_load_from_env(mock_env_vars, reload_config):
    """Test that API keys are loaded correctly from environment variables."""
    # Set the environment variables for this test
    mock_env_vars({
        "S2_API_KEY": "test_s2_key",
        "PUBMED_API_KEY": "test_pubmed_key",
        "OPENALEX_EMAIL": "test_openalex@example.com",
        "CROSSREF_MAILTO": "test_crossref@example.com",
    })
    
    # Reload the config module to pick up the new variables
    reload_config()

    # Assert that the values are now set
    assert config.S2_API_KEY == "test_s2_key"
    assert config.PUBMED_API_KEY == "test_pubmed_key"
    assert config.OPENALEX_EMAIL == "test_openalex@example.com"
    assert config.CROSSREF_MAILTO == "test_crossref@example.com"

def test_config_uses_defaults_when_env_is_empty(mock_env_vars, reload_config):
    """Test that default values are used when environment variables are not set."""
    # Ensure no relevant env vars are set for this test.
    # The mock_env_vars fixture will clean up anything set in other tests.
    # We can explicitly pass an empty dict or just not call it.
    # Let's explicitly clear them to be sure.
    mock_env_vars({
        "S2_API_KEY": "",
        "PUBMED_API_KEY": "",
        "OPENALEX_EMAIL": "",
        "CROSSREF_MAILTO": "",
        "LOG_FILE": ""
    })
    
    reload_config()

    # Assert that the values are the defaults (empty strings)
    assert config.S2_API_KEY == ""
    assert config.PUBMED_API_KEY == ""
    assert config.OPENALEX_EMAIL == ""
    assert config.CROSSREF_MAILTO == ""
    assert config.LOG_FILE == ""

def test_log_file_loads_from_env(mock_env_vars, reload_config):
    """Test that LOG_FILE is loaded from the environment variable."""
    mock_env_vars({"LOG_FILE": "app.log"})
    reload_config()
    assert config.LOG_FILE == "app.log"