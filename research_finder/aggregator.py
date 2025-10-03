from pathlib import Path

import logging
from typing import List, Iterator, Union
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
    
    def run_all_searches(self, query: str, limit: int, stream: bool = False) -> Union[List[dict], Iterator[dict]]:
        """
        Runs the search query on all added searchers.
        
        Args:
            query: Search query string.
            limit: Max results per source.
            stream: If True, returns a generator to avoid high memory usage.
        
        Returns:
            A list of all results, or a generator if stream=True.
        """
        self.logger.info(f"--- Starting search for '{query}' ---")
        seen_titles = set()
        seen_dois = set()
        successful_searchers = []
        failed_searchers = []

        if stream:
            def result_generator():
                for searcher in self.searchers:
                    self.logger.info(f"Searching {searcher.name}...")
                    try:
                        searcher.search(query, limit)
                        for result in searcher.get_results():
                            title = result.get('Title', '').lower().strip()
                            doi = result.get('DOI', '').lower().strip()
                            
                            if (title and title not in seen_titles) and \
                               (doi not in seen_dois or doi == 'n/a'):
                                seen_titles.add(title)
                                if doi != 'n/a':
                                    seen_dois.add(doi)
                                yield result
                        successful_searchers.append(searcher.name)
                    except Exception as e:
                        self.logger.error(f"An error occurred with searcher '{searcher.name}': {e}")
                        failed_searchers.append(searcher.name)
                
                # Log summary at the end of the generator
                self.logger.info(f"--- Search complete. ---")
                if successful_searchers:
                    self.logger.info(f"Successfully searched: {', '.join(successful_searchers)}")
                if failed_searchers:
                    self.logger.warning(f"Failed to search: {', '.join(failed_searchers)}")

            return result_generator()
        else:
            # Original implementation for backward compatibility
            all_results = []
            for searcher in self.searchers:
                self.logger.info(f"Searching {searcher.name}...")
                try:
                    searcher.search(query, limit)
                    for result in searcher.get_results():
                        title = result.get('Title', '').lower().strip()
                        doi = result.get('DOI', '').lower().strip()
                        
                        if (title and title not in seen_titles) and \
                           (doi not in seen_dois or doi == 'n/a'):
                            seen_titles.add(title)
                            if doi != 'n/a':
                                seen_dois.add(doi)
                            all_results.append(result)
                    successful_searchers.append(searcher.name)
                except Exception as e:
                    self.logger.error(f"An error occurred with searcher '{searcher.name}': {e}")
                    failed_searchers.append(searcher.name)
            
            # Log summary
            self.logger.info(f"--- Search complete. Total unique results found: {len(all_results)} ---")
            if successful_searchers:
                self.logger.info(f"Successfully searched: {', '.join(successful_searchers)}")
            if failed_searchers:
                self.logger.warning(f"Failed to search: {', '.join(failed_searchers)}")
            
            return all_results
    
    def clear_cache(self) -> None:
        """Clear all cached search results."""
        self.cache_manager.clear()
        
    def clear_expired_cache(self) -> None:
        """Remove only expired cache files."""
        self.cache_manager.clear_expired()