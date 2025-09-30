import requests
import logging
from .base_searcher import BaseSearcher

class SemanticScholarSearcher(BaseSearcher):
    """Searcher for the Semantic Scholar API."""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self):
        super().__init__("Semantic Scholar")
        self.logger = logging.getLogger(self.name)

    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        self.clear_results()
        # UPDATED: Added 'doi' and 'venue' to fields
        params = {
            'query': query,
            'limit': limit,
            'fields': 'title,authors,year,abstract,url,citationCount,tldr,doi,venue'
        }
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get('data', []):
                authors = [author.get('name') for author in item.get('authors', [])]
                # abstract = item.get('tldr', {}).get('text') or item.get('abstract')

                paper = {
                    'Title': item.get('title'),
                    'Authors': ', '.join(authors),
                    'Year': item.get('year'),
                    # 'Abstract': abstract,
                    'URL': item.get('url'),
                    'Source': self.name,
                    # Added Citation
                    'Citation': item.get('citationCount', 0),
                    # ADDED: DOI and Venue
                    'DOI': item.get('doi'),
                    'Venue': item.get('venue')
                }
                self.results.append(paper)
            self.logger.info(f"Found {len(self.results)} papers.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")