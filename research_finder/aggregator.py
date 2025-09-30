import logging
from typing import List
from .searchers.base_searcher import BaseSearcher

class Aggregator:
    """Aggregates results from multiple searchers."""
    
    def __init__(self):
        self.searchers: List[BaseSearcher] = []
        self.logger = logging.getLogger("Aggregator")

    def add_searcher(self, searcher: BaseSearcher) -> None:
        """Adds a searcher instance to the list."""
        if isinstance(searcher, BaseSearcher):
            self.searchers.append(searcher)
            self.logger.info(f"Added searcher: {searcher.name}")
        else:
            self.logger.error(f"Failed to add searcher: {searcher} is not a valid BaseSearcher instance.")

    def run_all_searches(self, query: str, limit: int) -> List[dict]:
        """
        Runs the search query on all added searchers and returns combined results.
        """
        self.logger.info(f"--- Starting search for '{query}' ---")
        all_results = []
        for searcher in self.searchers:
            try:
                searcher.search(query, limit)
                all_results.extend(searcher.get_results())
            except Exception as e:
                self.logger.error(f"An error occurred with searcher '{searcher.name}': {e}")
        
        self.logger.info(f"--- Search complete. Total results found: {len(all_results)} ---")
        return all_results