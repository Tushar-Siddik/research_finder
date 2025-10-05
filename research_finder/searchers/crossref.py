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

        if self._check_api_key("CrossRef 'mailto' email", self.mailto):
            self.rate_limit = CROSSREF_RATE_LIMIT_WITH_KEY
        else:
            self.rate_limit = CROSSREF_RATE_LIMIT_NO_KEY

    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        
        cached_results = self._get_from_cache(query, limit)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        params = {
            'query': query,
            'rows': limit,
            'select': 'title,author,container-title,DOI,created,license,URL,is-referenced-by-count'
        }
        
        if self.mailto:
            params['mailto'] = self.mailto
            self.logger.debug("Using 'mailto' for polite pool access.")
        else:
            self.logger.debug("No 'mailto' provided. Request will be unpolite.")

        try:
            self._enforce_rate_limit()
            
            self.logger.debug(f"Making GET request to {self.BASE_URL} with params: {params}")
            response = requests.get(self.BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            self.logger.debug(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            items = data.get('message', {}).get('items', [])
            self.logger.debug(f"Successfully parsed JSON. Found {len(items)} items in 'message.items' field.")
            
            for item in items:
                title_list = item.get('title', ['N/A'])
                authors = []
                for author in item.get('author', []):
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                
                year = 'N/A'
                created_date = item.get('created', {}).get('date-time', '')
                if created_date:
                    try:
                        year = datetime.fromisoformat(created_date.replace('Z', '+00:00')).year
                    except (ValueError, TypeError):
                        self.logger.warning(f"Could not parse date: {created_date}")

                venue_list = item.get('container-title', ['N/A'])
                
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
                self.logger.debug(f"Parsing paper: '{paper['Title'][:50]}...'")
                self.results.append(paper)
            
            self._save_to_cache(query, limit)
            self.logger.info(f"Found and stored {len(self.results)} papers from CrossRef.")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}", exc_info=True)