from pathlib import Path
import logging
from typing import List, Iterator, Union, Dict
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
        self.cache_manager = CacheManager(CACHE_DIR, CACHE_EXPIRY_HOURS)
        self.logger.info(f"Cache initialized at {CACHE_DIR} with expiry of {CACHE_EXPIRY_HOURS} hours")
        
        # --- ADD THESE INSTANCE VARIABLES ---
        self.last_successful_searchers: List[str] = []
        self.last_failed_searchers: List[str] = []

    def add_searcher(self, searcher: BaseSearcher) -> None:
        """Adds a searcher instance to the list."""
        if isinstance(searcher, BaseSearcher):
            searcher.cache_manager = self.cache_manager
            self.searchers.append(searcher)
            self.logger.info(f"Added searcher: {searcher.name}")
        else:
            self.logger.error(f"Failed to add searcher: {searcher} is not a valid BaseSearcher instance.")
    
    def run_all_searches(self, query: str, limit: int, stream: bool = False) -> Union[List[dict], Iterator[dict]]:
        """
        Runs the search query on all added searchers.
        """
        self.logger.info(f"--- Starting search for '{query}' ---")
        
        # --- RESET TRACKING VARIABLES FOR EACH RUN ---
        self.last_successful_searchers = []
        self.last_failed_searchers = []
        
        seen_dois = set()
        seen_titles_without_doi = set()

        if stream:
            def result_generator():
                for searcher in self.searchers:
                    self.logger.info(f"Searching {searcher.name}...")
                    try:
                        searcher.search(query, limit)
                        for result in searcher.get_results():
                            # ... (deduplication logic) ...
                            doi = result.get('DOI', '').lower().strip()
                            title = result.get('Title', '').lower().strip()

                            is_duplicate = False
                            if doi and doi != 'n/a':
                                if doi in seen_dois:
                                    is_duplicate = True
                                else:
                                    seen_dois.add(doi)
                            else: # No DOI available
                                if title in seen_titles_without_doi:
                                    is_duplicate = True
                                else:
                                    seen_titles_without_doi.add(title)
                            
                            if not is_duplicate:
                                yield result
                        # --- TRACK SUCCESS ---
                        self.last_successful_searchers.append(searcher.name)
                    except Exception as e:
                        self.logger.error(f"An error occurred with searcher '{searcher.name}': {e}")
                        # --- TRACK FAILURE ---
                        self.last_failed_searchers.append(searcher.name)
                
                self.logger.info("--- Search complete. ---")
            return result_generator()
        else:
            # Original implementation
            all_results = []
            for searcher in self.searchers:
                self.logger.info(f"Searching {searcher.name}...")
                try:
                    searcher.search(query, limit)
                    for result in searcher.get_results():
                        # ... (deduplication logic) ...
                        doi = result.get('DOI', '').lower().strip()
                        title = result.get('Title', '').lower().strip()

                        is_duplicate = False
                        if doi and doi != 'n/a':
                            if doi in seen_dois:
                                is_duplicate = True
                            else:
                                seen_dois.add(doi)
                        else: # No DOI available
                            if title in seen_titles_without_doi:
                                is_duplicate = True
                            else:
                                seen_titles_without_doi.add(title)
                        
                        if not is_duplicate:
                            all_results.append(result)
                    # --- TRACK SUCCESS ---
                    self.last_successful_searchers.append(searcher.name)
                except Exception as e:
                    self.logger.error(f"An error occurred with searcher '{searcher.name}': {e}")
                    # --- TRACK FAILURE ---
                    self.last_failed_searchers.append(searcher.name)
            
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
        """Clear all cached search results."""
        self.cache_manager.clear()
        
    def clear_expired_cache(self) -> None:
        """Remove only expired cache files."""
        self.cache_manager.clear_expired()