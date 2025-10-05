from pathlib import Path
import sys
from typing import Dict, Any
sys.path.append(str(Path(__file__).parent.parent.parent))
import requests
from .base_searcher import BaseSearcher
from config import SEMANTIC_SCHOLAR_API_URL, REQUEST_TIMEOUT, S2_API_KEY, SEMANTIC_SCHOLAR_RATE_LIMIT_WITH_KEY, SEMANTIC_SCHOLAR_RATE_LIMIT_NO_KEY
from ..utils import validate_doi, clean_author_list, normalize_year, normalize_string, normalize_citation_count

class SemanticScholarSearcher(BaseSearcher):
    """Searcher for the Semantic Scholar API."""
    
    BASE_URL = SEMANTIC_SCHOLAR_API_URL

    def __init__(self, cache_manager=None):
        super().__init__("Semantic Scholar", cache_manager)
        self.api_key = S2_API_KEY
        
        if self._check_api_key("Semantic Scholar API key", self.api_key):
            self.rate_limit = SEMANTIC_SCHOLAR_RATE_LIMIT_WITH_KEY
        else:
            self.rate_limit = SEMANTIC_SCHOLAR_RATE_LIMIT_NO_KEY

    def search(self, query: str, limit: int = 10, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit} by {search_type} with filters: {filters}")
        
        cached_results = self._get_from_cache(query, limit, search_type, filters)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        # Construct query based on search_type
        # S2 API doesn't have specific fields for title/author in this endpoint,
        # so we construct the query string for a best-effort search.
        api_query = query
        if search_type == 'title':
            api_query = f'"{query}"'
        elif search_type == 'author':
            api_query = f'author:"{query}"'
        
        params = {
            'query': api_query,
            'limit': limit,
            'fields': 'title,authors,year,abstract,url,citationCount,venue,openAccessPdf,externalIds'
        }
        
        # Add filters to params
        if filters:
            if filters.get('year_min') and filters.get('year_max'):
                params['year'] = f"{filters['year_min']}-{filters['year_max']}"
            elif filters.get('year_min'):
                params['year'] = f"{filters['year_min']}-"
            elif filters.get('year_max'):
                params['year'] = f"-{filters['year_max']}"
            
            if filters.get('min_citations'):
                params['minCitationCount'] = filters['min_citations']
        
        headers = {}
        if self.api_key:
            headers['x-api-key'] = self.api_key
            self.logger.debug("Using API key for request.")
        else:
            self.logger.debug("No API key provided. Request will be unauthenticated.")
        
        try:
            self._enforce_rate_limit()
            
            self.logger.debug(f"Making GET request to {self.BASE_URL} with params: {params}")
            
            response = requests.get(
                self.BASE_URL, 
                params=params, 
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            self.logger.debug(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            items = data.get('data', [])
            self.logger.debug(f"Successfully parsed JSON. Found {len(items)} items in 'data' field.")
            
            for item in items:
                authors_list = [author.get('name') for author in item.get('authors', [])]
                
                doi = 'N/A'
                external_ids = item.get('externalIds')
                if isinstance(external_ids, dict):
                    doi = external_ids.get('DOI', 'N/A')
                
                license_info = 'N/A'
                open_access_pdf = item.get('openAccessPdf', {})
                if open_access_pdf:
                    license_info = normalize_string(open_access_pdf.get('license'))

                paper = {
                    'Title': normalize_string(item.get('title')),
                    'Authors': clean_author_list(authors_list),
                    'Year': normalize_year(item.get('year')),
                    'URL': item.get('url'),
                    'Source': self.name,
                    'Citation Count': normalize_citation_count(item.get('citationCount', 0)),
                    'DOI': validate_doi(doi),
                    'Venue': normalize_string(item.get('venue')),
                    'License Type': license_info
                }
                self.logger.debug(f"Parsing paper: '{paper['Title'][:50]}...'")
                self.results.append(paper)
            
            self._save_to_cache(query, limit, search_type, filters)
            self.logger.info(f"Found and stored {len(self.results)} papers from Semantic Scholar.")
            
        except requests.exceptions.Timeout:
            self.logger.error("Request to Semantic Scholar API timed out.", exc_info=True)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error("Authentication failed. Please check your Semantic Scholar API key.", exc_info=True)
            elif e.response.status_code == 429:
                retry_after = e.response.headers.get('Retry-After', 'unknown')
                self.logger.error(f"Rate limit exceeded. Retry after {retry_after} seconds.", exc_info=True)
            elif e.response.status_code == 400:
                try:
                    error_content = e.response.json()
                    self.logger.error(f"Bad Request: {error_content}", exc_info=True)
                except:
                    self.logger.error(f"Bad Request: {e.response.text}", exc_info=True)
            else:
                self.logger.error(f"HTTP error occurred: {e}", exc_info=True)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}", exc_info=True)