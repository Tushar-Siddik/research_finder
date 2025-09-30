import requests
import logging
import time
from datetime import datetime
from .base_searcher import BaseSearcher
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Make the import more robust
try:
    from config import CROSSREF_API_URL, REQUEST_TIMEOUT, CROSSREF_RATE_LIMIT, CROSSREF_MAILTO
except ImportError:
    # Fallback values if config.py is missing or incomplete
    CROSSREF_API_URL = "https://api.crossref.org/works"
    REQUEST_TIMEOUT = 10
    CROSSREF_RATE_LIMIT = 1.0
    CROSSREF_MAILTO = "" # Default to empty string
    logging.warning("Could not import CrossRef settings from config.py. Using fallback values.")

class CrossrefSearcher(BaseSearcher):
    """Searcher for the CrossRef API."""
    
    BASE_URL = CROSSREF_API_URL
    _last_request_time = 0

    def __init__(self, cache_manager=None):
        super().__init__("CrossRef", cache_manager)
        self.logger = logging.getLogger(self.name)
        
        # Set attributes with fallbacks
        self.mailto = getattr(sys.modules[__name__], 'CROSSREF_MAILTO', "")
        self.rate_limit = getattr(sys.modules[__name__], 'CROSSREF_RATE_LIMIT', 1.0)
        
        if self.mailto:
            self.logger.info(f"Using CrossRef with polite pool email: {self.mailto}")
        else:
            self.logger.warning("No CrossRef email provided. Consider adding CROSSREF_MAILTO to your .env for better rate limits.")

    def _enforce_rate_limit(self):
        """Ensure we don't exceed the rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()

    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        
        # Try to get from cache first
        cached_results = self._get_from_cache(query, limit)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        # CrossRef uses a 'query' parameter for the search query
        # We use 'select' to specify which fields we want
        params = {
            'query': query,
            'rows': limit,
            'select': 'title,author,container-title,DOI,created,license,URL' # Select fields to return
        }
        
        # Add mailto for politeness and better rate limits
        if self.mailto:
            params['mailto'] = self.mailto

        try:
            self._enforce_rate_limit()
            
            response = requests.get(self.BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get('message', {}).get('items', []):
                # Title is often a list
                title_list = item.get('title', ['N/A'])
                title = title_list[0] if title_list else 'N/A'
                
                # Authors can be complex, we'll format them simply
                authors = []
                for author in item.get('author', []):
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                
                # Extract year from the 'created' date-time string
                year = 'N/A'
                created_date = item.get('created', {}).get('date-time', '')
                if created_date:
                    try:
                        year = datetime.fromisoformat(created_date.replace('Z', '+00:00')).year
                    except (ValueError, TypeError):
                        self.logger.warning(f"Could not parse date: {created_date}")

                # Venue (container-title) is also a list
                venue_list = item.get('container-title', ['N/A'])
                venue = venue_list[0] if venue_list else 'N/A'
                
                # License information can be a list of objects
                license_info = 'N/A'
                license_list = item.get('license', [])
                if license_list and isinstance(license_list, list) and len(license_list) > 0:
                    license_info = license_list[0].get('URL', 'N/A')

                paper = {
                    'Title': title,
                    'Authors': ', '.join(authors),
                    'Year': year,
                    'Venue': venue,
                    'Source': self.name,
                    'Citation Count': 'N/A', # CrossRef search doesn't provide citation count
                    'DOI': item.get('DOI'),
                    'License Type': license_info,
                    'URL': item.get('URL')
                }
                self.results.append(paper)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")