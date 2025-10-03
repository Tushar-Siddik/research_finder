"""
OpenAlex Searcher Module

This module provides a searcher for the OpenAlex API using the pyalex package.
OpenAlex is a free and open catalog of the global research system.
"""

import logging
from .base_searcher import BaseSearcher
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    import pyalex
    from pyalex import Works
    PYALEX_AVAILABLE = True
except ImportError:
    PYALEX_AVAILABLE = False
    Works = None

# Try to import from config to overwrite defaults
try:
    from config import OPENALEX_EMAIL
except ImportError:
    logging.warning("Could not import OPENALEX_EMAIL from config.py. Using default value.")
    OPENALEX_EMAIL = ""

class OpenAlexSearcher(BaseSearcher):
    """Searcher for the OpenAlex API using the pyalex package."""
    
    def __init__(self, cache_manager=None):
        if not PYALEX_AVAILABLE:
            raise ImportError("pyalex package not found. Install with 'pip install pyalex'")
        
        super().__init__("OpenAlex", cache_manager)
        
        # Use the check method for the email
        if self._check_api_key("OpenAlex 'polite pool' email", OPENALEX_EMAIL):
            pyalex.config.email = OPENALEX_EMAIL
            # With an email, we can be more aggressive
            self.rate_limit = 0.1  # 10 requests per second
        else:
            # Without an email, we should be more conservative
            self.rate_limit = 0.5  # 2 requests per second

    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        
        # Try to get from cache first
        cached_results = self._get_from_cache(query, limit)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        try:
            # Use the inherited rate limiting method
            self._enforce_rate_limit()
            
            # Define fields to select
            fields_to_select = (
                "id,display_name,publication_year,primary_location,"
                "authorships,cited_by_count,open_access,doi,type,best_oa_location"
            )
            
            # Execute the search query
            results = (
                Works()
                .search(query)
                .select(fields_to_select)
                .get(per_page=limit)
            )
            
            if not results:
                self.logger.info("No articles found in OpenAlex.")
                return

            for item in results:
                authors = [
                    authorship.get('author', {}).get('display_name') 
                    for authorship in item.get('authorships', [])
                ]
                
                primary_location = item.get('primary_location') or {}
                venue = primary_location.get('source', {}).get('display_name', 'N/A')
                
                license_info = 'N/A'
                oa_location = item.get('best_oa_location')
                if oa_location and oa_location.get('license'):
                    license_info = oa_location.get('license')

                paper = {
                    'Title': item.get('display_name'),
                    'Authors': ', '.join(authors),
                    'Year': item.get('publication_year'),
                    'Venue': venue,
                    'Source': self.name,
                    'Citation Count': item.get('cited_by_count', 0),
                    'DOI': item.get('doi'),
                    'License Type': license_info,
                    'URL': item.get('id')
                }
                self.results.append(paper)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
            
        except Exception as e:
            self.logger.error(f"An error occurred with OpenAlex search: {e}")