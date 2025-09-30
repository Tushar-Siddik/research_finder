import time
import logging
from .base_searcher import BaseSearcher

try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

class GoogleScholarSearcher(BaseSearcher):
    """Searcher for Google Scholar using the unofficial 'scholarly' library."""
    
    def __init__(self):
        if not scholarly:
            raise ImportError("scholarly library not found. Install with 'pip install scholarly'")
        super().__init__("Google Scholar")
        self.logger = logging.getLogger(self.name)

    def search(self, query: str, limit: int = 5) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}. (Caution: Unreliable)")
        self.clear_results()
        try:
            search_query = scholarly.search_pubs(query)
            for i, pub in enumerate(search_query):
                if i >= limit:
                    break
                paper = {
                    'Title': pub.get('bib', {}).get('title'),
                    'Authors': pub.get('bib', {}).get('author', ''),
                    'Year': pub.get('bib', {}).get('pub_year'),
                    'Abstract': pub.get('bib', {}).get('abstract'),
                    'URL': pub.get('pub_url'),
                    'Source': self.name
                }
                self.results.append(paper)
                time.sleep(1) # Be respectful to the server
            self.logger.info(f"Found {len(self.results)} papers.")
        except Exception as e:
            self.logger.error(f"Search failed: {e}. This is common with Google Scholar.")