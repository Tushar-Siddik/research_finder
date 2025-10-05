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
        
        if self._check_api_key("PubMed API key", self.api_key):
            self.rate_limit = PUBMED_RATE_LIMIT_WITH_KEY
        else:
            self.rate_limit = PUBMED_RATE_LIMIT_NO_KEY

    def _fetch_citation_count(self, pmid: str) -> int:
        """Fetch citation count for a PubMed ID using NIH iCite API."""
        if not pmid:
            return 0
        
        nih_url = f"https://icite.od.nih.gov/api/pubs?pmids={pmid}"
        try:
            time.sleep(0.2)  # 200ms delay
            self.logger.debug(f"Fetching citation count for PMID {pmid} from NIH iCite API.")
            nih_response = requests.get(nih_url, timeout=REQUEST_TIMEOUT)
            nih_response.raise_for_status()
            nih_data = nih_response.json().get('data', [])
            if nih_data:
                count = nih_data[0].get('citations', 0)
                self.logger.debug(f"NIH iCite returned citation count: {count} for PMID {pmid}")
                return count
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Could not fetch citation count for PMID {pmid}: {e}")
        except (ValueError, KeyError, IndexError):
            self.logger.warning(f"Error parsing citation data for PMID {pmid}.")
        
        return 0
    
    def search(self, query: str, limit: int = 10) -> None:
        self.logger.info(f"Searching for: '{query}' with limit {limit}")
        
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
                self.logger.debug("Using API key for PubMed request.")
            else:
                self.logger.debug("No API key provided for PubMed request.")
                
            self.logger.debug(f"Making ESEARCH request to {PUBMED_ESEARCH_URL} with params: {search_params}")
            search_response = requests.get(PUBMED_ESEARCH_URL, params=search_params, timeout=REQUEST_TIMEOUT)
            self.logger.debug(f"ESEARCH response status code: {search_response.status_code}")
            search_response.raise_for_status()
            search_data = search_response.json()
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            
            if not id_list:
                self.logger.info("No articles found in PubMed.")
                return

            self.logger.info(f"ESEARCH found {len(id_list)} PMIDs. Fetching details...")
            
            # Step 2: Use efetch to get details for the PMIDs
            self._enforce_rate_limit()
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(id_list),
                'retmode': 'xml'
            }
            if self.api_key:
                fetch_params['api_key'] = self.api_key

            self.logger.debug(f"Making EFETCH request to {PUBMED_EFETCH_URL} with params: {fetch_params}")
            fetch_response = requests.get(PUBMED_EFETCH_URL, params=fetch_params, timeout=REQUEST_TIMEOUT)
            self.logger.debug(f"EFETCH response status code: {fetch_response.status_code}")
            fetch_response.raise_for_status()
            
            root = ET.fromstring(fetch_response.content)
            
            for article in root.findall('.//PubmedArticle'):
                article_data = article.find('MedlineCitation').find('Article')
                
                title_elem = article_data.find('ArticleTitle')
                authors = []
                for author in article_data.findall('.//Author'):
                    last_name = author.find('LastName')
                    fore_name = author.find('ForeName')
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
                
                doi = 'N/A'
                article_id_list = article.find('PubmedData').find('ArticleIdList')
                if article_id_list is not None:
                    for aid in article_id_list.findall('ArticleId'):
                        if aid.get('IdType') == 'doi':
                            doi = aid.text
                            break
                
                license_info = 'N/A'
                
                pmid = article.find('MedlineCitation').get('PMID')
                if pmid:
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    citation_count = self._fetch_citation_count(pmid)
                else:
                    url = 'N/A'
                    citation_count = 0

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
                self.logger.debug(f"Parsing paper: '{paper['Title'][:50]}...'")
                self.results.append(paper)
            
            self._save_to_cache(query, limit)
            self.logger.info(f"Found and stored {len(self.results)} papers from PubMed.")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}", exc_info=True)
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse PubMed XML response: {e}", exc_info=True)