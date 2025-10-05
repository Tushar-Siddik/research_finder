# research_finder/searchers/openalex.py

"""
OpenAlex Searcher Module
"""

import logging
from .base_searcher import BaseSearcher
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from ..utils import validate_doi, clean_author_list, normalize_year, normalize_string, normalize_citation_count

try:
    import pyalex
    from pyalex import Works
    PYALEX_AVAILABLE = True
except ImportError:
    PYALEX_AVAILABLE = False
    Works = None

try:
    from config import OPENALEX_EMAIL, OPENALEX_RATE_LIMIT_WITH_EMAIL, OPENALEX_RATE_LIMIT_NO_EMAIL
except Exception as e:
    logging.warning(f"Could not import OpenAlex config from config.py. Using default values. Error: {e}")
    OPENALEX_EMAIL = ""
    OPENALEX_RATE_LIMIT_WITH_EMAIL = 0.1
    OPENALEX_RATE_LIMIT_NO_EMAIL = 0.5

class OpenAlexSearcher(BaseSearcher):
    """Searcher for the OpenAlex API using the pyalex package."""
    
    def __init__(self, cache_manager=None):
        if not PYALEX_AVAILABLE:
            raise ImportError("pyalex package not found. Install with 'pip install pyalex'")
        
        super().__init__("OpenAlex", cache_manager)
        
        if self._check_api_key("OpenAlex 'polite pool' email", OPENALEX_EMAIL):
            pyalex.config.email = OPENALEX_EMAIL
            self.rate_limit = OPENALEX_RATE_LIMIT_WITH_EMAIL
        else:
            self.rate_limit = OPENALEX_RATE_LIMIT_NO_EMAIL
    
    def search(self, query: str, limit: int = 10, search_type: str = 'keyword') -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit} by {search_type}")
        
        cached_results = self._get_from_cache(query, limit, search_type)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        try:
            self._enforce_rate_limit()
            
            fields_to_select = (
                "id,display_name,publication_year,primary_location,"
                "authorships,cited_by_count,open_access,doi,type,best_oa_location"
            )
            
            # Construct query based on search_type
            works_query = Works().select(fields_to_select)
            if search_type == 'title':
                works_query = works_query.filter(title={"search": query})
            elif search_type == 'author':
                works_query = works_query.filter(author={"display_name": query})
            else: # Default to keyword
                works_query = works_query.search(query)

            self.logger.debug(f"Executing pyalex query: {works_query}")
            results = works_query.get(per_page=limit)
            
            if not results:
                self.logger.info("No articles found in OpenAlex.")
                return

            self.logger.debug(f"Successfully retrieved {len(results)} results from OpenAlex.")

            for item in results:
                authors_list = [
                    authorship.get('author', {}).get('display_name') 
                    for authorship in item.get('authorships', [])
                ]
                
                primary_location = item.get('primary_location') or {}
                
                license_info = 'N/A'
                oa_location = item.get('best_oa_location')
                if oa_location and oa_location.get('license'):
                    license_info = normalize_string(oa_location.get('license'))

                paper = {
                    'Title': normalize_string(item.get('display_name')),
                    'Authors': clean_author_list(authors_list),
                    'Year': normalize_year(item.get('publication_year')),
                    'Venue': normalize_string(primary_location.get('source', {}).get('display_name', 'N/A')),
                    'Source': self.name,
                    'Citation Count': normalize_citation_count(item.get('cited_by_count', 0)),
                    'DOI': validate_doi(item.get('doi')),
                    'License Type': license_info,
                    'URL': item.get('id')
                }
                self.logger.debug(f"Parsing paper: '{paper['Title'][:50]}...'")
                self.results.append(paper)
            
            self._save_to_cache(query, limit, search_type)
            self.logger.info(f"Found and stored {len(self.results)} papers from OpenAlex.")
            
        except Exception as e:
            self.logger.error(f"An error occurred with OpenAlex search: {e}", exc_info=True)