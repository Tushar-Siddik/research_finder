import time
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
import requests

import feedparser
import logging
from .base_searcher import BaseSearcher
from config import ARXIV_API_URL, REQUEST_TIMEOUT, ARXIV_RATE_LIMIT

class ArxivSearcher(BaseSearcher):
    """Searcher for the arXiv API."""
    
    BASE_URL = ARXIV_API_URL
    _last_request_time = 0

    def __init__(self, cache_manager=None):
        super().__init__("arXiv", cache_manager)
        self.logger = logging.getLogger(self.name)
        self.rate_limit = ARXIV_RATE_LIMIT

    def _enforce_rate_limit(self):
        """Ensure we don't exceed the rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.RATE_LIMIT:
            sleep_time = self.RATE_LIMIT - time_since_last_request
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
        params = {
            'search_query': f'all:"{query}"',
            'start': 0,
            'max_results': limit
        }
        
        # Add a small delay before making the request
        self._enforce_rate_limit()
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                authors = [author.name for author in entry.authors]
                arxiv_id = entry.id.split('/')[-1]
                license_info = entry.get('rights', 'N/A')

                paper = {
                    'Title': entry.title,
                    'Authors': ', '.join(authors),
                    'Year': entry.published.split('-')[0],
                    # 'Abstract': entry.summary,
                    'URL': entry.link,
                    'Source': self.name,
                    'Citation Count': 'N/A',
                    # 'DOI': arxiv_id,
                    'DOI': f"10.48550/arXiv.{arxiv_id}" if arxiv_id else 'N/A',
                    'Venue': 'arXiv',
                    'License Type': license_info
                }
                self.results.append(paper)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
        except requests.exceptions.Timeout:
            self.logger.error("Request to arXiv API timed out")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to parse arXiv response: {e}")