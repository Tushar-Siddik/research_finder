"""
Caching module for the Research Article Finder tool.

This module provides the CacheManager class, which handles caching of search results
to avoid repeated API calls. It stores results in JSON files on disk, with a configurable
expiry time. Cache keys are generated based on query parameters to ensure that different
searches are cached separately.
"""

import os
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

class CacheManager:
    """
    Manages caching of search results to avoid repeated API calls.
    
    The cache stores results as JSON files on disk. Each cache entry is identified by a unique
    key generated from the search query, source, limit, search type, and filters. Cache entries
    have a configurable expiry time after which they are considered stale.
    """
    
    def __init__(self, cache_dir: str = "cache", expiry_hours: int = 24):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: The directory to store cache files.
            expiry_hours: The number of hours after which cache entries expire.
        """
        self.cache_dir = Path(cache_dir)
        self.expiry_seconds = expiry_hours * 3600
        self.logger = logging.getLogger("CacheManager")
        
        # Create the cache directory if it doesn't exist.
        self.cache_dir.mkdir(exist_ok=True)
        
    def _generate_cache_key(self, query: str, source: str, limit: int, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> str:
        """
        Generate a unique cache key based on query parameters.
        
        The key is a hash of a normalized string containing all relevant search parameters.
        This ensures that different queries, sources, or filters result in different cache files.
        
        Args:
            query: The search query.
            source: The source name (e.g., "arXiv", "Semantic Scholar").
            limit: The maximum number of results.
            search_type: The type of search ('keyword', 'title', 'author').
            filters: A dictionary of filters applied to the search.
            
        Returns:
            A unique MD5 hash to be used as the cache filename.
        """
        # Create a string representation of the filters for the key.
        filter_str = ""
        if filters:
            # Sort filters to ensure consistent key generation regardless of dict order.
            sorted_filters = sorted(filters.items())
            filter_str = "_" + "_".join(f"{k}_{v}" for k, v in sorted_filters if v is not None)
        
        # Create a normalized string from the parameters.
        key_string = f"{query.lower()}_{source}_{limit}_{search_type}{filter_str}"
        # Generate a hash to use as filename.
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the full path to a cache file given its key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """
        Check if a cache file exists and is not expired.
        
        Args:
            cache_path: The Path object for the cache file.
            
        Returns:
            True if the cache is valid, False otherwise.
        """
        if not cache_path.exists():
            return False
            
        # Check if the file's modification time is within the expiry period.
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.expiry_seconds
    
    def get(self, query: str, source: str, limit: int, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached results for a given set of search parameters.
        
        Args:
            query: The search query.
            source: The source name.
            limit: The maximum number of results.
            search_type: The type of search.
            filters: The filters applied to the search.
            
        Returns:
            The cached list of results if found and valid, otherwise None.
        """
        cache_key = self._generate_cache_key(query, source, limit, search_type, filters)
        cache_path = self._get_cache_path(cache_key)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    self.logger.info(f"Cache hit for {source} query: '{query}' (type: {search_type}, filters: {filters})")
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error reading cache file {cache_path}: {e}")
        
        self.logger.info(f"Cache miss for {source} query: '{query}' (type: {search_type}, filters: {filters})")
        return None
    
    def set(self, query: str, source: str, limit: int, results: List[Dict[str, Any]], search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        """
        Store search results in the cache.
        
        Args:
            query: The search query.
            source: The source name.
            limit: The maximum number of results.
            results: The search results to cache.
            search_type: The type of search.
            filters: The filters applied to the search.
        """
        if not results:
            self.logger.debug(f"No results to cache for {source} query: '{query}'")
            return
            
        cache_key = self._generate_cache_key(query, source, limit, search_type, filters)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False)
                self.logger.info(f"Cached {len(results)} results for {source} query: '{query}' (type: {search_type}, filters: {filters})")
        except IOError as e:
            self.logger.error(f"Error writing to cache file {cache_path}: {e}")
    
    def clear(self) -> None:
        """Clear all cached files."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.logger.info("Cache cleared successfully")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def clear_expired(self) -> None:
        """Remove only expired cache files."""
        try:
            removed_count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                if not self._is_cache_valid(cache_file):
                    cache_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Removed {removed_count} expired cache files")
        except Exception as e:
            self.logger.error(f"Error clearing expired cache files: {e}")