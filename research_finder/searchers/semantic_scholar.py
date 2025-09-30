import time
import requests
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

import logging
from .base_searcher import BaseSearcher
from config import SEMANTIC_SCHOLAR_API_URL, REQUEST_TIMEOUT, S2_API_KEY, SEMANTIC_SCHOLAR_RATE_LIMIT

class SemanticScholarSearcher(BaseSearcher):
    """Searcher for the Semantic Scholar API."""
    
    BASE_URL = SEMANTIC_SCHOLAR_API_URL
    _last_request_time = 0  # Class variable to track last request time

    def __init__(self, cache_manager=None):
        super().__init__("Semantic Scholar", cache_manager)
        self.logger = logging.getLogger(self.name)
        self.api_key = S2_API_KEY
        self.rate_limit = SEMANTIC_SCHOLAR_RATE_LIMIT
        
        if self.api_key:
            self.logger.info(f"Using Semantic Scholar API key with rate limit of {self.rate_limit} request(s) per second")
        else:
            self.logger.warning("No Semantic Scholar API key found. Using unauthenticated requests with lower rate limits.")

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
        
        # We use 'externalIds' to get the DOI.
        params = {
            'query': query,
            'limit': limit,
            'fields': 'title,authors,year,abstract,url,citationCount,venue,openAccessPdf,externalIds'
        }
        
        # Set up headers with API key if available
        headers = {}
        if self.api_key:
            headers['x-api-key'] = self.api_key
        
        try:
            # Enforce rate limit before making the request
            self._enforce_rate_limit()
            
            self.logger.debug(f"Making request to {self.BASE_URL} with params: {params}")
            
            response = requests.get(
                self.BASE_URL, 
                params=params, 
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            data = response.json()
            
            for item in data.get('data', []):
                authors = [author.get('name') for author in item.get('authors', [])]
                
                # CORRECTED: Extract DOI from externalIds
                external_ids = item.get('externalIds', {})
                doi = external_ids.get('DOI', 'N/A')
                
                # Extract license information
                open_access_pdf = item.get('openAccessPdf', {})
                license_info = open_access_pdf.get('license') if open_access_pdf else 'N/A'

                paper = {
                    'Title': item.get('title'),
                    'Authors': ', '.join(authors),
                    'Year': item.get('year'),
                    'URL': item.get('url'),
                    'Source': self.name,
                    'Citation Count': item.get('citationCount', 0),
                    'DOI': doi,  # Now correctly extracted
                    'Venue': item.get('venue'),
                    'License Type': license_info
                }
                self.results.append(paper)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
            
        except requests.exceptions.Timeout:
            self.logger.error("Request to Semantic Scholar API timed out")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error("Authentication failed. Please check your Semantic Scholar API key.")
            elif e.response.status_code == 429:
                retry_after = e.response.headers.get('Retry-After', 'unknown')
                self.logger.error(f"Rate limit exceeded. Retry after {retry_after} seconds.")
            elif e.response.status_code == 400:
                try:
                    error_content = e.response.json()
                    self.logger.error(f"Bad Request: {error_content}")
                except:
                    self.logger.error(f"Bad Request: {e.response.text}")
            else:
                self.logger.error(f"HTTP error occurred: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")