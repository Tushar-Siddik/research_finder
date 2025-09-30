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
        # UPDATED: Added 'openAccessPdf.license' to the fields to retrieve
        params = {
            'query': query,
            'limit': limit,
            'fields': 'title,authors,year,abstract,url,citationCount,tldr,doi,venue,openAccessPdf.license'
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get('data', []):
                authors = [author.get('name') for author in item.get('authors', [])]
                abstract = item.get('tldr', {}).get('text') or item.get('abstract')
                
                # UPDATED: Extract license information
                license_info = item.get('openAccessPdf', {}).get('license') or 'N/A'

                paper = {
                    'Title': item.get('title'),
                    'Authors': ', '.join(authors),
                    'Year': item.get('year'),
                    # 'Abstract': abstract,
                    'URL': item.get('url'),
                    'Source': self.name,
                    'Citation Count': item.get('citationCount', 0),
                    'DOI': item.get('doi'),
                    'Venue': item.get('venue'),
                    'License Type': license_info
                }
                self.results.append(paper)
            self.logger.info(f"Found {len(self.results)} papers.")
        
        except requests.exceptions.Timeout:
            self.logger.error("Request to Semantic Scholar API timed out")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")