from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseSearcher(ABC):
    """Abstract base class for all article searchers."""
    
    def __init__(self, name: str, cache_manager=None):
        self.name = name
        self.results: List[Dict[str, Any]] = []
        self.cache_manager = cache_manager

    @abstractmethod
    def search(self, query: str, limit: int) -> None:
        """
        Performs a search and populates the self.results list.
        Each result should be a dictionary.
        """
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