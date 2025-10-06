"""
Pytest-style tests for the cache.py module.

This test suite verifies the functionality of the CacheManager class, including
key generation, setting, getting, and clearing cache entries, as well as
handling of expiry times.
"""

import os
import pytest
import json
import time
from pathlib import Path
from research_finder.cache import CacheManager

# Sample data to be used in tests
SAMPLE_RESULTS = [
    {'id': 1, 'title': 'Test Paper 1'},
    {'id': 2, 'title': 'Test Paper 2'}
]
EMPTY_RESULTS = []

@pytest.fixture
def cache_manager(tmp_path):
    """
    Pytest fixture to create a CacheManager instance with a temporary directory
    and a short expiry time for testing.
    """
    # Use a temporary directory for the cache to avoid polluting the project.
    # Set expiry to 1 second for fast testing of expiration logic.
    return CacheManager(cache_dir=str(tmp_path), expiry_hours=1/3600)

class TestCacheManager:
    """Test suite for the CacheManager class."""

    def test_init_creates_cache_dir(self, tmp_path):
        """Test that the CacheManager creates the cache directory on initialization."""
        cache_dir = tmp_path / "new_cache_dir"
        assert not cache_dir.exists()
        CacheManager(cache_dir=str(cache_dir))
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_generate_cache_key_consistency(self, cache_manager):
        """Test that the same parameters always generate the same cache key."""
        key1 = cache_manager._generate_cache_key(
            query="test query", source="arxiv", limit=10
        )
        key2 = cache_manager._generate_cache_key(
            query="test query", source="arxiv", limit=10
        )
        assert key1 == key2

    def test_generate_cache_key_uniqueness(self, cache_manager):
        """Test that different parameters generate different cache keys."""
        base_params = {"query": "test query", "source": "arxiv", "limit": 10}
        key1 = cache_manager._generate_cache_key(**base_params)
        
        # Different query
        key2 = cache_manager._generate_cache_key(query="another query", **{k: v for k, v in base_params.items() if k != 'query'})
        assert key1 != key2

        # Different source
        key3 = cache_manager._generate_cache_key(source="semantic scholar", **{k: v for k, v in base_params.items() if k != 'source'})
        assert key1 != key3

        # Different limit
        key4 = cache_manager._generate_cache_key(limit=20, **{k: v for k, v in base_params.items() if k != 'limit'})
        assert key1 != key4

        # Different search_type
        key5 = cache_manager._generate_cache_key(search_type="author", **base_params)
        assert key1 != key5

        # With filters
        key6 = cache_manager._generate_cache_key(filters={"year": "2023"}, **base_params)
        assert key1 != key6

        # Filters in different order should produce the same key
        key7 = cache_manager._generate_cache_key(filters={"year": "2023", "author": "Doe"}, **base_params)
        key8 = cache_manager._generate_cache_key(filters={"author": "Doe", "year": "2023"}, **base_params)
        assert key7 == key8
        assert key1 != key7

    def test_get_cache_miss(self, cache_manager):
        """Test retrieving from cache when no entry exists."""
        result = cache_manager.get(query="nonexistent", source="test", limit=10)
        assert result is None

    def test_set_and_get_cache_hit(self, cache_manager):
        """Test storing and then successfully retrieving from cache."""
        cache_manager.set(query="test query", source="test", limit=10, results=SAMPLE_RESULTS)
        result = cache_manager.get(query="test query", source="test", limit=10)
        
        assert result is not None
        assert result == SAMPLE_RESULTS

    def test_set_overwrites_existing_cache(self, cache_manager):
        """Test that calling set again with the same key overwrites the old data."""
        cache_manager.set(query="test query", source="test", limit=10, results=SAMPLE_RESULTS)
        
        new_results = [{'id': 3, 'title': 'New Test Paper'}]
        cache_manager.set(query="test query", source="test", limit=10, results=new_results)
        
        result = cache_manager.get(query="test query", source="test", limit=10)
        assert result == new_results

    def test_get_expired_cache_miss(self, cache_manager):
        """Test that an expired cache entry is treated as a miss."""
        cache_manager.set(query="expiring query", source="test", limit=10, results=SAMPLE_RESULTS)
        
        # Wait for the cache to expire (expiry is 1 second)
        time.sleep(1.1)
        
        result = cache_manager.get(query="expiring query", source="test", limit=10)
        assert result is None

    def test_set_does_not_cache_empty_results(self, cache_manager):
        """Test that calling set with an empty list does not create a cache file."""
        cache_manager.set(query="empty query", source="test", limit=10, results=EMPTY_RESULTS)
        
        cache_path = cache_manager._get_cache_path(
            cache_manager._generate_cache_key(query="empty query", source="test", limit=10)
        )
        assert not cache_path.exists()

    def test_clear_removes_all_cache_files(self, cache_manager):
        """Test that the clear method removes all files from the cache directory."""
        # Create a few cache files
        cache_manager.set(query="query1", source="test", limit=10, results=SAMPLE_RESULTS)
        cache_manager.set(query="query2", source="test", limit=10, results=SAMPLE_RESULTS)
        
        # Verify files exist
        assert len(list(cache_manager.cache_dir.glob("*.json"))) == 2
        
        # Clear the cache
        cache_manager.clear()
        
        # Verify files are gone
        assert len(list(cache_manager.cache_dir.glob("*.json"))) == 0

    def test_clear_expired_removes_only_expired_files(self, cache_manager):
        """Test that clear_expired removes only the stale cache files."""
        import time
        
        # Create a valid cache entry
        cache_manager.set(query="valid query", source="test", limit=10, results=[{'id': 1}])
        
        # Create an expired cache entry by manually setting its mtime to the past
        cache_manager.set(query="expiring query", source="test", limit=10, results=[{'id': 2}])
        expired_path = cache_manager._get_cache_path(
            cache_manager._generate_cache_key(query="expiring query", source="test", limit=10)
        )
        # Set file's modification time to 2 hours ago (expiry is 1 hour)
        past_time = time.time() - (2 * 3600)
        os.utime(expired_path, (past_time, past_time))

        # Verify two files exist before clearing
        assert len(list(cache_manager.cache_dir.glob("*.json"))) == 2
        
        # Clear only expired files
        cache_manager.clear_expired()
        
        # Verify only one file remains
        remaining_files = list(cache_manager.cache_dir.glob("*.json"))
        assert len(remaining_files) == 1
        
        # Verify the correct file remains by checking its content
        with open(remaining_files[0], 'r') as f:
            data = json.load(f)
            assert data == [{'id': 1}]

    def test_corrupted_cache_file_is_handled(self, cache_manager, caplog):
        """Test that a corrupted JSON file in the cache is handled gracefully."""
        cache_key = cache_manager._generate_cache_key(query="corrupt", source="test", limit=10)
        cache_path = cache_manager._get_cache_path(cache_key)
        
        # Write a non-JSON file to simulate corruption
        with open(cache_path, 'w') as f:
            f.write("this is not valid json")
            
        # Attempting to get it should return None and log an error
        result = cache_manager.get(query="corrupt", source="test", limit=10)
        assert result is None
        # Check for the generic error message you wrote in the code
        assert "Error reading cache file" in caplog.text