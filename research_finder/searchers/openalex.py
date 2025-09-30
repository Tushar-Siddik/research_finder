import logging
from .base_searcher import BaseSearcher

try:
    import pyalex
    from pyalex import Works
    PYALEX_AVAILABLE = True
except ImportError:
    PYALEX_AVAILABLE = False
    Works = None

class OpenAlexSearcher(BaseSearcher):
    """Searcher for the OpenAlex API using the pyalex package."""
    
    def __init__(self, cache_manager=None):
        if not PYALEX_AVAILABLE:
            raise ImportError("pyalex package not found. Install with 'pip install pyalex'")
        
        super().__init__("OpenAlex", cache_manager)
        self.logger = logging.getLogger(self.name)
        
        # The library recommends setting a polite email for better rate limits
        # You can set your email here if you want
        # pyalex.config.email = "your.email@example.com"
        
        self.logger.info("Using OpenAlex via the pyalex package.")

    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        
        # Try to get from cache first
        cached_results = self._get_from_cache(query, limit)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        try:
            # Use pyalex to search for works
            self.logger.debug(f"Querying OpenAlex for '{query}'")
            
            # Fields to select
            fields_to_select = [
                "id",
                "display_name",
                "publication_year",
                "primary_location",
                "authorships",
                "cited_by_count",
                "open_access",
                "doi",
                "type",
                "best_oa_location"
            ]
            
            results = (
                Works()
                .filter(**{"default.search": query})
                .select(fields_to_select)
                .get(per_page=limit)
            )
            
            if not results:
                self.logger.info("No articles found in OpenAlex.")
                return

            for item in results:
                # Extract authors from the authorships list
                authors = [
                    authorship.get('author', {}).get('display_name') 
                    for authorship in item.get('authorships', [])
                ]
                
                # Extract venue (journal name)
                primary_location = item.get('primary_location') or {}
                venue = primary_location.get('source', {}).get('display_name', 'N/A')
                
                # Extract license information from the best open access location
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
                    'URL': item.get('id')  # The OpenAlex URL for the work
                }
                self.results.append(paper)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
            
        except Exception as e:
            self.logger.error(f"An error occurred with OpenAlex search: {e}")