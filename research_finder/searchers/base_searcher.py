"""
Abstract base class for all article searchers.

This module defines the BaseSearcher class, which serves as a template for all specific
searcher implementations (e.g., SemanticScholarSearcher, ArxivSearcher). It enforces a
common interface for searching, rate limiting, and caching, ensuring that all searchers
behave consistently.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import time

class BaseSearcher(ABC):
    """
    Abstract base class for all article searchers.
    
    This class provides shared functionality for all searchers, including rate limiting,
    result management, and caching. Subclasses must implement the `search` method.
    """
    
    def __init__(self, name: str, cache_manager=None):
        """
        Initialize the base searcher.
        
        Args:
            name: The display name of the searcher (e.g., "Semantic Scholar").
            cache_manager: An optional CacheManager instance for caching results.
        """
        self.name = name
        self.results: List[Dict[str, Any]] = []
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(self.name)
        
        # Used by the rate limiting mechanism to track the last request time.
        self._last_request_time = 0
        # Default rate limit (requests per second). Subclasses should override this.
        self.rate_limit = 1.0

    @abstractmethod
    def search(self, query: str, limit: int, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        """
        Performs a search and populates the self.results list.
        
        This method must be implemented by all subclasses. It should fetch results from the
        respective API, parse them into a standardized format, and store them in self.results.
        
        Args:
            query: The search term.
            limit: The maximum number of results to return.
            search_type: The type of search ('keyword', 'title', 'author').
            filters: A dictionary of filters to apply.
        """
        pass

    def get_results(self) -> List[Dict[str, Any]]:
        """Returns the list of standardized results from the last search."""
        return self.results

    def clear_results(self) -> None:
        """Clears the stored results from the last search."""
        self.results = []
        
    def _get_from_cache(self, query: str, limit: int, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> Optional[List[Dict[str, Any]]]:
        """Try to get results from the cache manager before performing a search."""
        if self.cache_manager:
            return self.cache_manager.get(query, self.name, limit, search_type, filters)
        return None
        
    def _save_to_cache(self, query: str, limit: int, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        """Save the results from the last search to the cache manager."""
        if self.cache_manager and self.results:
            self.cache_manager.set(query, self.name, limit, self.results, search_type, filters)

    def _check_api_key(self, key_name: str, key_value: str) -> bool:
        """
        Checks if an API key is available, logs a message, and returns a boolean.
        
        This is a helper method to standardize how searchers check for API keys.
        
        Args:
            key_name: The name of the API key (e.g., "Semantic Scholar API key").
            key_value: The value of the API key.
            
        Returns:
            True if the key is present, False otherwise.
        """
        if not key_value:
            self.logger.warning(f"No {key_name} provided. Rate limits will be very low and some features may not work.")
            return False
        self.logger.info(f"Using {key_name}.")
        return True

    def _enforce_rate_limit(self):
        """
        Pauses execution if necessary to ensure we don't exceed the configured rate limit.
        
        This method should be called before making any network request to an API.
        It calculates the time elapsed since the last request and sleeps if that time
        is less than the configured rate limit.
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        # Update the last request time to now.
        self._last_request_time = time.time()