from pathlib import Path
import sys
from typing import Dict, Any
sys.path.append(str(Path(__file__).parent.parent.parent))
import requests
import feedparser
from .base_searcher import BaseSearcher
from config import ARXIV_API_URL, REQUEST_TIMEOUT, ARXIV_RATE_LIMIT
from ..utils import validate_doi, clean_author_list, normalize_year, normalize_string 

class ArxivSearcher(BaseSearcher):
    """Searcher for the arXiv API."""
    
    BASE_URL = ARXIV_API_URL

    def __init__(self, cache_manager=None):
        super().__init__("arXiv", cache_manager)
        self.rate_limit = ARXIV_RATE_LIMIT
        self.logger.info(f"arXiv searcher initialized with rate limit: {self.rate_limit} req/s")

    
    def search(self, query: str, limit: int = 10, search_type: str = 'keyword', filters: Dict[str, Any] = None) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit} by {search_type}")
        
        cached_results = self._get_from_cache(query, limit, search_type)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        if search_type == 'title':
            search_query = f'ti:"{query}"'
        elif search_type == 'author':
            search_query = f'au:"{query}"'
        else: # Default to keyword
            search_query = f'all:"{query}"'
        
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': limit
        }
        
        self._enforce_rate_limit()
        
        try:
            self.logger.debug(f"Making GET request to {self.BASE_URL} with params: {params}")
            response = requests.get(self.BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            self.logger.debug(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            entries = feed.entries
            self.logger.debug(f"Successfully parsed feed. Found {len(entries)} entries.")

            for entry in entries:
                authors_list = [author.name for author in entry.authors]
                
                doi = 'N/A'
                arxiv_id = entry.id.split('/')[-1] if entry.id else None
                if arxiv_id and arxiv_id.replace('v', '').replace('.', '').isdigit():
                    constructed_doi = f"10.48550/arXiv.{arxiv_id}"
                    if validate_doi(constructed_doi) != 'N/A':
                        doi = constructed_doi

                paper = {
                    'Title': normalize_string(entry.title),
                    'Authors': clean_author_list(authors_list),
                    'Year': normalize_year(entry.published.split('-')[0]),
                    'URL': entry.link,
                    'Source': self.name,
                    'Citation Count': 'N/A',
                    'DOI': doi,
                    'Venue': 'arXiv',
                    'License Type': normalize_string(entry.get('rights', 'N/A'))
                }
                self.logger.debug(f"Parsing paper: '{paper['Title'][:50]}...'")
                self.results.append(paper)
            
            self._save_to_cache(query, limit, search_type)
            self.logger.info(f"Found and stored {len(self.results)} papers from arXiv.")
            
        except requests.exceptions.Timeout:
            self.logger.error("Request to arXiv API timed out.", exc_info=True)
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}", exc_info=True)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Failed to parse arXiv response: {e}", exc_info=True)
