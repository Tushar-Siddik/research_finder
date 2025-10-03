import time
import requests
import xml.etree.ElementTree as ET
from .base_searcher import BaseSearcher
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import PUBMED_ESEARCH_URL, PUBMED_EFETCH_URL, REQUEST_TIMEOUT, PUBMED_API_KEY, PUBMED_RATE_LIMIT_WITH_KEY, PUBMED_RATE_LIMIT_NO_KEY
from ..utils import validate_doi, clean_author_list, normalize_year, normalize_string

class PubmedSearcher(BaseSearcher):
    """Searcher for the PubMed API (Entrez) with an API key."""

    def __init__(self, cache_manager=None):
        super().__init__("PubMed", cache_manager)
        self.api_key = PUBMED_API_KEY
        
        # Use the new check method and adjust rate limit accordingly
        if self._check_api_key("PubMed API key", self.api_key):
            # With an API key, the limit is 10 requests per second
            self.rate_limit = PUBMED_RATE_LIMIT_WITH_KEY  # 0.1: 1/10 = 0.1s between requests
        else:
            # Without a key, the limit is 3 requests per second
            self.rate_limit = PUBMED_RATE_LIMIT_NO_KEY  # 0.33: ~1/3 = 0.33s between requests

    def _fetch_citation_count(self, pmid: str) -> int:
        """
        Fetch citation count for a PubMed ID using NIH iCite API.
        This is a separate API call, so we add a small delay to be polite.
        """
        if not pmid:
            return 0
        
        nih_url = f"https://icite.od.nih.gov/api/pubs?pmids={pmid}"
        try:
            # Be polite to the iCite API with a small delay
            time.sleep(0.2)  # 200ms delay
            nih_response = requests.get(nih_url, timeout=REQUEST_TIMEOUT)
            nih_response.raise_for_status()
            nih_data = nih_response.json().get('data', [])
            if nih_data:
                return nih_data[0].get('citations', 0)
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Could not fetch citation count for PMID {pmid}: {e}")
        except (ValueError, KeyError, IndexError):
            self.logger.warning(f"Error parsing citation data for PMID {pmid}.")
        
        return 0  # Return 0 if we can't get the count
    
    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        
        # Try to get from cache first
        cached_results = self._get_from_cache(query, limit)
        if cached_results:
            self.results = cached_results
            return
            
        self.clear_results()
        
        try:
            # Step 1: Use esearch to get a list of PMIDs
            self._enforce_rate_limit()
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmode': 'json',
                'retmax': limit
            }
            if self.api_key:
                search_params['api_key'] = self.api_key
                
            self.logger.debug(f"Searching PubMed with params: {search_params}")
            search_response = requests.get(
                PUBMED_ESEARCH_URL, 
                params=search_params, 
                timeout=REQUEST_TIMEOUT
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            
            if not id_list:
                self.logger.info("No articles found in PubMed.")
                return

            # Step 2: Use efetch to get details for the PMIDs
            self._enforce_rate_limit()
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(id_list),
                'retmode': 'xml'
            }
            if self.api_key:
                fetch_params['api_key'] = self.api_key

            self.logger.debug(f"Fetching details for {len(id_list)} PMIDs.")
            fetch_response = requests.get(PUBMED_EFETCH_URL, params=fetch_params, timeout=REQUEST_TIMEOUT)
            fetch_response.raise_for_status()
            
            # Parse the XML response
            root = ET.fromstring(fetch_response.content)
            
            for article in root.findall('.//PubmedArticle'):
                article_data = article.find('MedlineCitation').find('Article')
                
                title_elem = article_data.find('ArticleTitle')
                # title = itle_elem.text if title_elem is not None else 'N/A'
                
                authors = []
                for author in article_data.findall('.//Author'):
                    last_name = author.find('LastName')
                    fore_name = author.find('ForeName')
                    # Handle cases where names might be collective
                    if last_name is not None and fore_name is not None:
                        authors.append(f"{fore_name.text} {last_name.text}")
                    elif last_name is not None:
                        authors.append(last_name.text)
                
                year = 'N/A'
                journal_issue = article_data.find('Journal').find('JournalIssue')
                if journal_issue is not None:
                    pub_date = journal_issue.find('PubDate')
                    if pub_date is not None:
                        year_elem = pub_date.find('Year')
                        if year_elem is not None:
                            year = year_elem.text
                
                venue_elem = article_data.find('Journal').find('Title')
                # venue = venue_elem.text if venue_elem is not None else 'N/A'
                
                # DOI is often in the ArticleIdList
                doi = 'N/A'
                article_id_list = article.find('PubmedData').find('ArticleIdList')
                if article_id_list is not None:
                    for aid in article_id_list.findall('ArticleId'):
                        if aid.get('IdType') == 'doi':
                            doi = aid.text
                            break
                
                # PubMed doesn't provide license info in the standard fetch
                license_info = 'N/A'
                
                # Construct the PubMed URL
                pmid = article.find('MedlineCitation').get('PMID')
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

                # Fetch citation count safely
                citation_count = self._fetch_citation_count(pmid)

                paper = {
                    'Title': normalize_string(title_elem.text if title_elem is not None else 'N/A'),
                    'Authors': clean_author_list(authors),
                    'Year': normalize_year(year),
                    'Venue': normalize_string(venue_elem.text if venue_elem is not None else 'N/A'),
                    'Source': self.name,
                    'Citation Count': citation_count,
                    'DOI': validate_doi(doi),
                    'License Type': license_info,
                    'URL': url
                }
                self.results.append(paper)
            
            # Save to cache
            self._save_to_cache(query, limit)
            self.logger.info(f"Found {len(self.results)} papers.")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse PubMed XML response: {e}")