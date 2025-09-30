from pathlib import Path

import logging
from typing import List
from .searchers.base_searcher import BaseSearcher
from .cache import CacheManager
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import CACHE_DIR, CACHE_EXPIRY_HOURS

class Aggregator:
    """Aggregates results from multiple searchers."""
    
    def __init__(self):
        self.searchers: List[BaseSearcher] = []
        self.logger = logging.getLogger("Aggregator")
        # Initialize cache manager
        self.cache_manager = CacheManager(CACHE_DIR, CACHE_EXPIRY_HOURS)
        self.logger.info(f"Cache initialized at {CACHE_DIR} with expiry of {CACHE_EXPIRY_HOURS} hours")

    def add_searcher(self, searcher: BaseSearcher) -> None:
        """Adds a searcher instance to the list."""
        if isinstance(searcher, BaseSearcher):
            # Set the cache manager for the searcher
            searcher.cache_manager = self.cache_manager
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
        seen_titles = set()  # Track seen titles to avoid duplicates
        
        total_searchers = len(self.searchers)
        for i, searcher in enumerate(self.searchers, 1):
            print(f"Searching {searcher.name} ({i}/{total_searchers})...")
            try:
                searcher.search(query, limit)
                for result in searcher.get_results():
                    title = result.get('Title', '').lower().strip()
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        all_results.append(result)
            except Exception as e:
                self.logger.error(f"An error occurred with searcher '{searcher.name}': {e}")
        
        self.logger.info(f"--- Search complete. Total results found: {len(all_results)} ---")
        return all_results
    
    def clear_cache(self) -> None:
        """Clear all cached search results."""
        self.cache_manager.clear()
        
    def clear_expired_cache(self) -> None:
        """Remove only expired cache files."""
        self.cache_manager.clear_expired()