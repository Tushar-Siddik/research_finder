from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSearcher(ABC):
    """Abstract base class for all article searchers."""
    
    def __init__(self, name: str):
        self.name = name
        self.results: List[Dict[str, Any]] = []

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