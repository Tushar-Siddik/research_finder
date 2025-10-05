"""
Aggregator module for the Research Article Finder tool.

This module contains the Aggregator class, which is responsible for coordinating
searches across multiple data sources (searchers). It manages the search process,
aggregates results, and handles de-duplication based on DOI and title.
"""

from pathlib import Path
import logging
from typing import List, Iterator, Union, Dict, Any
from .searchers.base_searcher import BaseSearcher
from .cache import CacheManager
from tqdm import tqdm
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import CACHE_DIR, CACHE_EXPIRY_HOURS

class Aggregator:
    """
    Aggregates results from multiple searchers.
    
    This class takes a user's query, runs it against all configured searchers,
    and then merges the results, removing duplicates. It provides a summary of
    which searches succeeded or failed and manages the overall search process.
    """
    
    def __init__(self):
        """Initializes the Aggregator, setting up the cache and logger."""
        self.searchers: List[BaseSearcher] = []
        self.logger = logging.getLogger("Aggregator")
        self.cache_manager = CacheManager(CACHE_DIR, CACHE_EXPIRY_HOURS)
        self.logger.info(f"Cache initialized at {CACHE_DIR} with expiry of {CACHE_EXPIRY_HOURS} hours")
        
        # Track the success or failure of the last run for reporting.
        self.last_successful_searchers: List[str] = []
        self.last_failed_searchers: List[str] = []

    def add_searcher(self, searcher: BaseSearcher) -> None:
        """
        Adds a searcher instance to the list of active searchers.
        
        Args:
            searcher: An instance of a class that inherits from BaseSearcher.
        """
        if isinstance(searcher, BaseSearcher):
            # Provide the searcher with the shared cache manager.
            searcher.cache_manager = self.cache_manager
            self.searchers.append(searcher)
            self.logger.info(f"Added searcher: {searcher.name}")
        else:
            self.logger.error(f"Failed to add searcher: {searcher} is not a valid BaseSearcher instance.")
    
    def _process_searchers(self, query: str, limit: int, search_type: str, filters: Dict[str, Any]) -> Iterator[dict]:
        """
        Internal helper to iterate through searchers, find articles, and yield unique results.
        
        This generator function contains the core logic for running searches and performing
        de-duplication. It yields one unique article at a time, which is memory-efficient.
        
        Args:
            query: The search query.
            limit: The maximum number of results to yield.
            search_type: The type of search ('keyword', 'title', 'author').
            filters: A dictionary of filters to apply.
            
        Yields:
            A dictionary representing a unique article.
        """
        # Reset tracking for this run.
        self.last_successful_searchers = []
        self.last_failed_searchers = []
        
        # Use sets to keep track of seen DOIs and titles for de-duplication.
        seen_dois = set()
        seen_titles_without_doi = set()
        total_yielded = 0

        # Use tqdm to display a progress bar for the user.
        pbar = tqdm(self.searchers, desc="Searching Vendors", unit="source", file=sys.stdout)
        
        for searcher in pbar:
            pbar.set_postfix_str(f"Current: {searcher.name}")
            
            try:
                # Execute the search on the current searcher.
                searcher.search(query, limit, search_type, filters)
                raw_results = searcher.get_results()
                self.logger.debug(f"{searcher.name} returned {len(raw_results)} raw results.")
                
                # Process each result from the searcher.
                for result in raw_results:
                    doi = result.get('DOI', '').lower().strip()
                    title = result.get('Title', '').lower().strip()

                    is_duplicate = False
                    duplicate_reason = ""
                    
                    # De-duplication logic: prioritize DOI as it's a unique identifier.
                    if doi and doi != 'n/a':
                        if doi in seen_dois:
                            is_duplicate = True
                            duplicate_reason = "DOI"
                        else:
                            seen_dois.add(doi)
                    else: # If no DOI, fall back to title matching.
                        if title in seen_titles_without_doi:
                            is_duplicate = True
                            duplicate_reason = "Title"
                        else:
                            seen_titles_without_doi.add(title)
                    
                    # Yield the result only if it's not a duplicate.
                    if not is_duplicate:
                        total_yielded += 1
                        self.logger.debug(f"Yielding unique result: '{title[:50]}...'")
                        yield result
                    else:
                        self.logger.debug(f"Skipping duplicate result by {duplicate_reason}: '{title[:50]}...'")
                
                self.last_successful_searchers.append(searcher.name)
                self.logger.info(f"Finished searching {searcher.name}. Found {len(raw_results)} results.")

            except Exception as e:
                # Catch any exception from a single searcher to avoid crashing the entire process.
                self.logger.error(f"An error occurred with searcher '{searcher.name}': {e}", exc_info=True)
                self.last_failed_searchers.append(searcher.name)
        
        pbar.close()
        self.logger.info(f"Aggregation complete. Total unique articles yielded: {total_yielded}")

    def run_all_searches(self, query: str, limit: int, search_type: str = 'keyword', filters: Dict[str, Any] = None, stream: bool = False) -> Union[List[dict], Iterator[dict]]:
        """
        Runs the search query on all added searchers.
        
        This is the main public method of the Aggregator. It can either return a generator
        for memory-efficient streaming or a list for convenience.
        
        Args:
            query: The search query.
            limit: The maximum number of results per source.
            search_type: The type of search.
            filters: A dictionary of filters to apply.
            stream: If True, returns a generator; otherwise, returns a list.
            
        Returns:
            A generator or list of unique article dictionaries.
        """
        self.logger.info(f"--- Starting search for '{query}' (type: {search_type}, filters: {filters}) across {len(self.searchers)} vendors ---")

        if stream:
            # For streaming, return the generator directly to save memory.
            return self._process_searchers(query, limit, search_type, filters or {})
        else:
            # For non-streaming, consume the generator into a list.
            all_results = list(self._process_searchers(query, limit, search_type, filters or {}))
            self.logger.info(f"--- Search complete. Total unique results found: {len(all_results)} ---")
            return all_results

    def get_last_run_summary(self) -> Dict[str, List[str]]:
        """
        Returns a summary of the last search run.
        
        Returns:
            A dictionary with keys 'successful' and 'failed' containing lists of searcher names.
        """
        return {
            'successful': self.last_successful_searchers,
            'failed': self.last_failed_searchers
        }
    
    def clear_cache(self) -> None:
        """Clear all cached search results via the cache manager."""
        self.cache_manager.clear()
        
    def clear_expired_cache(self) -> None:
        """Remove only expired cache files via the cache manager."""
        self.cache_manager.clear_expired()