import time
import logging
import re
from .base_searcher import BaseSearcher
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import REQUEST_TIMEOUT

try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

class GoogleScholarSearcher(BaseSearcher):
    """Searcher for Google Scholar using the unofficial 'scholarly' library."""
    
    def __init__(self, cache_manager=None):
        if not scholarly:
            raise ImportError("scholarly library not found. Install with 'pip install scholarly'")
        super().__init__("Google Scholar", cache_manager)
        self.logger = logging.getLogger(self.name)
        self.logger.warning("Google Scholar has no official API. Rate limiting is important to avoid being blocked.")

    def search(self, query: str, limit: int = 5) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}. (Caution: Unreliable)")
        
        # Try to get from cache first
        cached_results = self._get_from_cache(query, limit)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        try:
            search_query = scholarly.search_pubs(query)
            for i, pub in enumerate(search_query):
                if i >= limit:
                    break
                
                doi = None
                url = pub.get('pub_url', '')
                if 'doi.org/' in url:
                    doi = url.split('doi.org/')[-1]

                paper = {
                    'Title': pub.get('bib', {}).get('title'),
                    'Authors': pub.get('bib', {}).get('author', ''),
                    'Year': pub.get('bib', {}).get('pub_year'),
                    'URL': url,
                    'Source': self.name,
                    'Citation Count': pub.get('bib', {}).get('num_citations', 'N/A'),
                    'DOI': doi,
                    'Venue': pub.get('bib', {}).get('journal', ''),
                    'License Type': 'N/A'
                }
                self.results.append(paper)
                
                # Add rate limiting
                time.sleep(2)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}. This is common with Google Scholar.")