import time
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
import requests

import feedparser
import logging
from .base_searcher import BaseSearcher
from config import ARXIV_API_URL, REQUEST_TIMEOUT

class ArxivSearcher(BaseSearcher):
    """Searcher for the arXiv API."""
    
    # BASE_URL = "http://export.arxiv.org/api/query"
    BASE_URL = ARXIV_API_URL

    def __init__(self):
        super().__init__("arXiv")
        self.logger = logging.getLogger(self.name)

    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        self.clear_results()
        
        # Add a small delay before making the request
        time.sleep(0.5)
        
        params = {
            'search_query': f'all:"{query}"',
            'start': 0,
            'max_results': limit
        }
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                authors = [author.name for author in entry.authors]
                arxiv_id = entry.id.split('/')[-1]
                
                # UPDATED: Extract license information
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
                    # ADDED: New fields
                    'License Type': license_info
                }
                self.results.append(paper)
            self.logger.info(f"Found {len(self.results)} papers.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to parse arXiv response: {e}")