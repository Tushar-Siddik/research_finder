"""
Searcher for Google Scholar using the unofficial 'scholarly' library.

This module implements the GoogleScholarSearcher class. It's important to note that Google Scholar
has no official API, and this scraper is unreliable and can be blocked. Rate limiting is
critical when using this searcher.
"""

from .base_searcher import BaseSearcher
from pathlib import Path
import sys
from typing import Dict, Any
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import GOOGLE_SCHOLAR_RATE_LIMIT
from ..utils import validate_doi, clean_author_list, normalize_year, normalize_string, normalize_citation_count

try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

class GoogleScholarSearcher(BaseSearcher):
    """Searcher for Google Scholar using the unofficial 'scholarly' library."""
    
    def __init__(self, cache_manager=None):
        """
        Initializes the GoogleScholarSearcher.
        
        Args:
            cache_manager: An optional CacheManager instance.
        """
        if not scholarly:
            raise ImportError("scholarly library not found. Install with 'pip install scholarly'")
        super().__init__("Google Scholar", cache_manager)
        # Set a very conservative rate limit to avoid being blocked.
        self.rate_limit = GOOGLE_SCHOLAR_RATE_LIMIT
        self.logger.warning("Google Scholar has no official API. Rate limiting is critical to avoid being blocked.")
    
    def search(self, query: str, limit: int = 5, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        """
        Searches Google Scholar for articles matching the given criteria.
        
        Args:
            query: The search term.
            limit: The maximum number of results to return.
            search_type: The type of search ('keyword', 'title', 'author').
            filters: A dictionary of filters to apply (year, citations). Note: these are applied post-search.
        """
        self.logger.info(f"Searching for: '{query}' with limit {limit} by {search_type} with filters: {filters}. (Caution: Unreliable)")
        
        cached_results = self._get_from_cache(query, limit, search_type, filters)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        try:
            # Construct the query based on the search type.
            search_query = query
            if search_type == 'title':
                search_query = f'"{query}"' # Exact phrase match.
            elif search_type == 'author':
                # For author search, we could use scholarly.search_author, but it returns profiles, not papers.
                # We stick to a keyword search for consistency.
                search_query = f"author:{query}"

            self.logger.debug(f"Starting scholarly search for query: '{search_query}'")
            search_query_gen = scholarly.search_pubs(search_query)
            
            # Fetch more results than needed to account for post-search filtering.
            for i, pub in enumerate(search_query_gen):
                if i >= limit * 2:
                    self.logger.debug(f"Reached fetch limit. Stopping search.")
                    break
                
                # Enforce rate limit between each result fetch.
                self._enforce_rate_limit()

                doi = None
                url = pub.get('pub_url', '')
                if 'doi.org/' in url:
                    doi = url.split('doi.org/')[-1]

                paper = {
                    'Title': normalize_string(pub.get('bib', {}).get('title')),
                    'Authors': clean_author_list(pub.get('bib', {}).get('author', '')),
                    'Year': normalize_year(pub.get('bib', {}).get('pub_year')),
                    'URL': url,
                    'Source': self.name,
                    'Citation Count': normalize_citation_count(pub.get('bib', {}).get('num_citations', 'N/A')),
                    'DOI': validate_doi(doi),
                    'Venue': normalize_string(pub.get('bib', {}).get('journal', '')),
                    'License Type': 'N/A'
                }
                
                # Apply post-search filtering for year and citations since the API doesn't support it.
                year = normalize_year(paper.get('bib', {}).get('pub_year'))
                citations = normalize_citation_count(pub.get('bib', {}).get('num_citations', 'N/A'))

                if filters:
                    if filters.get('year_min') and year != 'n.d.' and int(year) < filters['year_min']:
                        continue
                    if filters.get('year_max') and year != 'n.d.' and int(year) > filters['year_max']:
                        continue
                    if filters.get('min_citations') and citations < filters['min_citations']:
                        continue
                
                self.results.append(paper)
                if len(self.results) >= limit:
                    break
            
            self._save_to_cache(query, limit, search_type, filters)
            self.logger.info(f"Found and stored {len(self.results)} papers from Google Scholar.")
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}. This is common with Google Scholar.", exc_info=True)