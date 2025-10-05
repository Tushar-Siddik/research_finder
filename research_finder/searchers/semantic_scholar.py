"""
Searcher for the Semantic Scholar API.

This module implements the SemanticScholarSearcher class, which interacts with the Semantic Scholar
Graph API to find academic papers. It supports searching by keyword, title, and author, and
can filter results by year and citation count.
"""

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
        """
        Initializes the SemanticScholarSearcher.
        
        Args:
            cache_manager: An optional CacheManager instance.
        """
        super().__init__("Semantic Scholar", cache_manager)
        self.api_key = S2_API_KEY
        
        # Adjust the rate limit based on whether an API key is provided.
        if self._check_api_key("Semantic Scholar API key", self.api_key):
            self.rate_limit = SEMANTIC_SCHOLAR_RATE_LIMIT_WITH_KEY
        else:
            self.rate_limit = SEMANTIC_SCHOLAR_RATE_LIMIT_NO_KEY

    def search(self, query: str, limit: int = 10, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        """
        Searches Semantic Scholar for papers matching the given criteria.
        
        Args:
            query: The search term.
            limit: The maximum number of results to return.
            search_type: The type of search ('keyword', 'title', 'author').
            filters: A dictionary of filters to apply (year, citations).
        """
        self.logger.info(f"Searching for: '{query}' with limit {limit} by {search_type} with filters: {filters}")
        
        # Check cache before making an API request.
        cached_results = self._get_from_cache(query, limit, search_type, filters)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        # Construct the query based on the search type.
        # S2 API doesn't have specific fields for title/author in this endpoint,
        # so we construct the query string for a best-effort search.
        api_query = query
        if search_type == 'title':
            api_query = f'"{query}"' # Exact phrase match for title.
        elif search_type == 'author':
            api_query = f'author:"{query}"' # Search within author field.
        
        params = {
            'query': api_query,
            'limit': limit,
            'fields': 'title,authors,year,abstract,url,citationCount,venue,openAccessPdf,externalIds'
        }
        
        # Add filters to the request parameters.
        if filters:
            if filters.get('year_min') and filters.get('year_max'):
                params['year'] = f"{filters['year_min']}-{filters['year_max']}"
            elif filters.get('year_min'):
                params['year'] = f"{filters['year_min']}-"
            elif filters.get('year_max'):
                params['year'] = f"-{filters['year_max']}"
            
            if filters.get('min_citations'):
                params['minCitationCount'] = filters['min_citations']
        
        # Set up headers, including the API key if available.
        headers = {}
        if self.api_key:
            headers['x-api-key'] = self.api_key
            self.logger.debug("Using API key for request.")
        else:
            self.logger.debug("No API key provided. Request will be unauthenticated.")
        
        try:
            # Enforce rate limit before making the request.
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
            
            # Parse the JSON response and extract paper details.
            items = data.get('data', [])
            self.logger.debug(f"Successfully parsed JSON. Found {len(items)} items in 'data' field.")
            
            for item in items:
                authors_list = [author.get('name') for author in item.get('authors', [])]
                
                # Extract DOI from the externalIds field.
                doi = 'N/A'
                external_ids = item.get('externalIds')
                if isinstance(external_ids, dict):
                    doi = external_ids.get('DOI', 'N/A')
                
                # Extract license information from the openAccessPdf field.
                license_info = 'N/A'
                open_access_pdf = item.get('openAccessPdf', {})
                if open_access_pdf:
                    license_info = normalize_string(open_access_pdf.get('license'))

                # Standardize the paper data into the common format.
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
            
            # Save the results to cache.
            self._save_to_cache(query, limit, search_type, filters)
            self.logger.info(f"Found and stored {len(self.results)} papers from Semantic Scholar.")
            
        except requests.exceptions.Timeout:
            self.logger.error("Request to Semantic Scholar API timed out.", exc_info=True)
        except requests.exceptions.HTTPError as e:
            # Handle specific HTTP errors like authentication or rate limiting.
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