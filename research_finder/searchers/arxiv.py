import requests
import feedparser
import logging
from .base_searcher import BaseSearcher

class ArxivSearcher(BaseSearcher):
    """Searcher for the arXiv API."""
    
    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        super().__init__("arXiv")
        self.logger = logging.getLogger(self.name)

    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        self.clear_results()
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
                # UPDATED: Extract arXiv ID to use as DOI
                arxiv_id = entry.id.split('/')[-1]
                
                paper = {
                    'Title': entry.title,
                    'Authors': ', '.join(authors),
                    'Year': entry.published.split('-')[0],
                    # 'Abstract': entry.summary,
                    'URL': entry.link,
                    'Source': self.name,
                    'Citation': 'N/A',
                    # ADDED: Use arXiv ID and set Venue
                    'DOI': arxiv_id,
                    'Venue': 'arXiv'
                }
                self.results.append(paper)
            self.logger.info(f"Found {len(self.results)} papers.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to parse arXiv response: {e}")