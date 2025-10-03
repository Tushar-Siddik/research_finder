from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import time

class BaseSearcher(ABC):
    """Abstract base class for all article searchers."""
    
    def __init__(self, name: str, cache_manager=None):
        self.name = name
        self.results: List[Dict[str, Any]] = []
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(self.name)
        # Use an instance variable for rate limiting
        self._last_request_time = 0
        # Default rate limit, can be overridden by subclasses
        self.rate_limit = 1.0 

    @abstractmethod
    def search(self, query: str, limit: int) -> None:
        """Performs a search and populates the self.results list."""
        pass

    def get_results(self) -> List[Dict[str, Any]]:
        """Returns the list of standardized results."""
        return self.results

    def clear_results(self) -> None:
        """Clears the stored results."""
        self.results = []
        
    def _get_from_cache(self, query: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """Try to get results from cache."""
        if self.cache_manager:
            return self.cache_manager.get(query, self.name, limit)
        return None
        
    def _save_to_cache(self, query: str, limit: int) -> None:
        """Save results to cache."""
        if self.cache_manager and self.results:
            self.cache_manager.set(query, self.name, limit, self.results)

    def _check_api_key(self, key_name: str, key_value: str) -> bool:
        """Checks if an API key is available, logs a message, and returns a boolean."""
        if not key_value:
            self.logger.warning(f"No {key_name} provided. Rate limits will be very low and some features may not work.")
            return False
        self.logger.info(f"Using {key_name}.")
        return True

    def _enforce_rate_limit(self):
        """Ensure we don't exceed the rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()