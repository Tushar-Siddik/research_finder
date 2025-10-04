import requests
from datetime import datetime
from .base_searcher import BaseSearcher
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import CROSSREF_API_URL, REQUEST_TIMEOUT, CROSSREF_MAILTO, CROSSREF_RATE_LIMIT_WITH_KEY, CROSSREF_RATE_LIMIT_NO_KEY
from ..utils import validate_doi, clean_author_list, normalize_year, normalize_string, normalize_citation_count

class CrossrefSearcher(BaseSearcher):
    """Searcher for the CrossRef API."""
    
    BASE_URL = CROSSREF_API_URL

    def __init__(self, cache_manager=None):
        super().__init__("CrossRef", cache_manager)
        self.mailto = CROSSREF_MAILTO

        # CrossRef uses a 'mailto' for its polite pool.
        if self._check_api_key("CrossRef 'mailto' email", self.mailto):
            # The polite pool has a higher limit.
            self.rate_limit = CROSSREF_RATE_LIMIT_WITH_KEY  # 1: 1 request per second
        else:
            # We should be extra polite if not identifying ourselves.
            self.rate_limit = CROSSREF_RATE_LIMIT_NO_KEY  # 1 request every 2 seconds

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
            'select': 'title,author,container-title,DOI,created,license,URL,is-referenced-by-count' # Select fields to return
        }
        
        # Add mailto for politeness and better rate limits
        if self.mailto:
            params['mailto'] = self.mailto

        try:
            self._enforce_rate_limit()
            
            response = requests.get(
                self.BASE_URL, 
                params=params, 
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            for item in data.get('message', {}).get('items', []):
                # Title is often a list
                title_list = item.get('title', ['N/A'])
                # title = normalize_string(title_list[0] if title_list else 'N/A')
                
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
                # venue = venue_list[0] if venue_list else 'N/A'
                
                # License information can be a list of objects
                license_info = 'N/A'
                license_list = item.get('license', [])
                if license_list and isinstance(license_list, list) and len(license_list) > 0:
                    license_info = license_list[0].get('URL', 'N/A')

                paper = {
                    'Title': normalize_string(title_list[0] if title_list else 'N/A'),
                    'Authors': clean_author_list(authors),
                    'Year': normalize_year(year),
                    'Venue': normalize_string(venue_list[0] if venue_list else 'N/A'),
                    'Source': self.name,
                    'Citation Count': normalize_citation_count(item.get('is-referenced-by-count', 0)),
                    'DOI': validate_doi(item.get('DOI')),
                    'License Type': license_info,
                    'URL': item.get('URL')
                }
                self.results.append(paper)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")