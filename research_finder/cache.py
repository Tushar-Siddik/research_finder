import os
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

class CacheManager:
    """Manages caching of search results to avoid repeated API calls."""
    
    def __init__(self, cache_dir: str = "cache", expiry_hours: int = 24):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            expiry_hours: Number of hours after which cache entries expire
        """
        self.cache_dir = Path(cache_dir)
        self.expiry_seconds = expiry_hours * 3600
        self.logger = logging.getLogger("CacheManager")
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
    def _generate_cache_key(self, query: str, source: str, limit: int) -> str:
        """
        Generate a unique cache key based on query parameters.
        
        Args:
            query: Search query
            source: Source name (e.g., "arXiv", "Semantic Scholar")
            limit: Maximum number of results
            
        Returns:
            A unique cache key
        """
        # Create a normalized string from the parameters
        key_string = f"{query.lower()}_{source}_{limit}"
        # Generate a hash to use as filename
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the full path to a cache file."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """
        Check if a cache file exists and is not expired.
        
        Args:
            cache_path: Path to the cache file
            
        Returns:
            True if cache is valid, False otherwise
        """
        if not cache_path.exists():
            return False
            
        # Check if file is older than expiry time
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.expiry_seconds
    
    def get(self, query: str, source: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached results for a query.
        
        Args:
            query: Search query
            source: Source name
            limit: Maximum number of results
            
        Returns:
            Cached results if available and valid, None otherwise
        """
        cache_key = self._generate_cache_key(query, source, limit)
        cache_path = self._get_cache_path(cache_key)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    self.logger.info(f"Cache hit for {source} query: '{query}'")
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error reading cache file {cache_path}: {e}")
        
        return None
    
    def set(self, query: str, source: str, limit: int, results: List[Dict[str, Any]]) -> None:
        """
        Store search results in cache.
        
        Args:
            query: Search query
            source: Source name
            limit: Maximum number of results
            results: Search results to cache
        """
        if not results:
            return
            
        cache_key = self._generate_cache_key(query, source, limit)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False)
                self.logger.info(f"Cached {len(results)} results for {source} query: '{query}'")
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