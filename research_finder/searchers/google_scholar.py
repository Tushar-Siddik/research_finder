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
        if not scholarly:
            raise ImportError("scholarly library not found. Install with 'pip install scholarly'")
        super().__init__("Google Scholar", cache_manager)
        self.rate_limit = GOOGLE_SCHOLAR_RATE_LIMIT
        self.logger.warning("Google Scholar has no official API. Rate limiting is critical to avoid being blocked.")
    
    def search(self, query: str, limit: int = 5, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit} by {search_type} with filters: {filters}. (Caution: Unreliable)")
        
        cached_results = self._get_from_cache(query, limit, search_type, filters)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        try:
            # Construct query based on search_type
            search_query = query
            if search_type == 'title':
                search_query = f'"{query}"' # Exact phrase match
            elif search_type == 'author':
                # For author search, we can try to find publications by a specific author
                # scholarly.search_author is more robust but returns author profiles, not publications directly.
                # We'll stick to a keyword search for consistency.
                search_query = f"author:{query}"

            self.logger.debug(f"Starting scholarly search for query: '{search_query}'")
            search_query_gen = scholarly.search_pubs(search_query)
            
            for i, pub in enumerate(search_query_gen):
                if i >= limit * 2: # Fetch more to account for post-filtering
                    self.logger.debug(f"Reached fetch limit. Stopping search.")
                    break
                
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
                
                # Post-search filtering for year and citations
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
                
                self.logger.debug(f"Parsing paper {i+1}: '{paper['Title'][:50]}...'")
                self.results.append(paper)
            
            self._save_to_cache(query, limit, search_type, filters)
            self.logger.info(f"Found and stored {len(self.results)} papers from Google Scholar.")
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}. This is common with Google Scholar.", exc_info=True)