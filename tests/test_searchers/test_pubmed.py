"""
Pytest-style tests for the pubmed.py searcher module.

This test suite verifies the functionality of the PubmedSearcher class, including
initialization with and without an API key, the two-step search process (esearch/efetch),
XML parsing, citation count fetching, filtering, caching, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

from research_finder.searchers.pubmed import PubmedSearcher
import requests.exceptions

# --- Mock Data for PubMed API Responses ---

@pytest.fixture
def sample_pubmed_xml():
    """A mock XML response from the PubMed efetch API."""
    return """<PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation PMID="12345678">
                <Article>
                    <ArticleTitle>A Study on RNA Viruses</ArticleTitle>
                    <Journal>
                        <JournalIssue>
                            <PubDate>
                                <Year>2021</Year>
                            </PubDate>
                        </JournalIssue>
                        <Title>Virology Journal</Title>
                    </Journal>
                    <AuthorList>
                        <Author>
                            <ForeName>John</ForeName><LastName>Doe</LastName>
                        </Author>
                        <Author>
                            <LastName>Smith</LastName>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
            <PubmedData>
                <ArticleIdList>
                    <ArticleId IdType="doi">10.1234/virology.2021.01</ArticleId>
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
        <PubmedArticle>
            <MedlineCitation PMID="87654321">
                <Article>
                    <ArticleTitle>Another Paper on DNA</ArticleTitle>
                    <Journal>
                        <JournalIssue>
                            <PubDate>
                                <Year>2020</Year>
                            </PubDate>
                        </JournalIssue>
                        <Title>Genetics Today</Title>
                    </Journal>
                    <AuthorList>
                        <Author>
                            <ForeName>Jane</ForeName><LastName>Doe</LastName>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
            <PubmedData>
                <ArticleIdList>
                    <!-- No DOI for this paper -->
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
    </PubmedArticleSet>"""

@pytest.fixture
def pubmed_searcher_with_key(mock_cache_manager):
    """Provides a PubmedSearcher instance with an API key."""
    with patch('research_finder.searchers.pubmed.PUBMED_API_KEY', 'TEST_KEY'):
        return PubmedSearcher(cache_manager=mock_cache_manager)

@pytest.fixture
def pubmed_searcher_no_key(mock_cache_manager):
    """Provides a PubmedSearcher instance without an API key."""
    with patch('research_finder.searchers.pubmed.PUBMED_API_KEY', None):
        return PubmedSearcher(cache_manager=mock_cache_manager)

# --- Test Suite ---

class TestPubmedSearcher:
    """Test suite for the PubmedSearcher class."""

    def test_init_with_key_sets_correct_rate_limit(self, pubmed_searcher_with_key):
        """Test that providing an API key sets the correct rate limit."""
        assert pubmed_searcher_with_key.name == "PubMed"
        assert pubmed_searcher_with_key.api_key == 'TEST_KEY'
        assert pubmed_searcher_with_key.rate_limit == 0.1 # Polite limit

    def test_init_without_key_sets_correct_rate_limit(self, pubmed_searcher_no_key):
        """Test that not providing an API key sets the unpolite rate limit."""
        assert pubmed_searcher_no_key.api_key is None
        assert pubmed_searcher_no_key.rate_limit == 0.33 # Unpolite limit

    @patch('time.sleep') # Mock sleep to speed up the test
    @patch('research_finder.searchers.pubmed.requests.get')
    def test_search_keyword_query(self, mock_get, mock_sleep, pubmed_searcher_with_key, sample_pubmed_xml):
        """Test a standard keyword search and XML parsing."""
        # Mock the four API calls: esearch, efetch, and two NIH iCite calls
        esearch_response = MagicMock()
        esearch_response.json.return_value = {'esearchresult': {'idlist': ['12345678', '87654321']}}
        efetch_response = MagicMock()
        efetch_response.content = sample_pubmed_xml.encode('utf-8')
        nih_response_1 = MagicMock() # Mock for the first paper's citations
        nih_response_1.json.return_value = {'data': [{'citations': 25}]}
        nih_response_2 = MagicMock() # Mock for the second paper's citations
        nih_response_2.json.return_value = {'data': [{'citations': 10}]}
        
        # Add all four mock responses to the side_effect list
        mock_get.side_effect = [esearch_response, efetch_response, nih_response_1, nih_response_2]

        pubmed_searcher_with_key.search("RNA viruses", limit=10)

        # Assert API was called four times
        assert mock_get.call_count == 4
        
        # Assert esearch call was correct
        esearch_params = mock_get.call_args_list[0][1]['params']
        assert esearch_params['term'] == "RNA viruses"
        assert esearch_params['api_key'] == 'TEST_KEY'

        # Assert efetch call was correct
        efetch_params = mock_get.call_args_list[1][1]['params']
        assert efetch_params['id'] == '12345678,87654321'
        
        # Assert results were parsed correctly
        assert len(pubmed_searcher_with_key.results) == 2
        result1 = pubmed_searcher_with_key.results[0]
        assert result1['Title'] == 'A Study on RNA Viruses'
        assert result1['Authors'] == 'John Doe, Smith'
        assert result1['Year'] == '2021'
        assert result1['Venue'] == 'Virology Journal'
        assert result1['DOI'] == '10.1234/virology.2021.01'
        assert result1['URL'] == 'https://pubmed.ncbi.nlm.nih.gov/12345678/'
        assert result1['Citation Count'] == 25 # From mocked NIH iCite response

    @patch('time.sleep') # Mock sleep to speed up the test
    @patch('research_finder.searchers.pubmed.requests.get')
    def test_search_title_and_author_queries(self, mock_get, mock_sleep, pubmed_searcher_with_key, sample_pubmed_xml):
        """Test that title and author search terms are constructed correctly."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {'esearchresult': {'idlist': ['12345678', '87654321']}}
        efetch_response = MagicMock()
        efetch_response.content = sample_pubmed_xml.encode('utf-8')
        nih_response_1 = MagicMock() # Mock for the first paper's citations
        nih_response_1.json.return_value = {'data': [{'citations': 15}]}
        nih_response_2 = MagicMock() # Mock for the second paper's citations
        nih_response_2.json.return_value = {'data': [{'citations': 8}]}
        
        # Add all four mock responses to the side_effect list
        mock_get.side_effect = [esearch_response, efetch_response, nih_response_1, nih_response_2]

        # Test title search
        pubmed_searcher_with_key.search("RNA viruses", search_type='title')
        esearch_params = mock_get.call_args_list[0][1]['params']
        assert esearch_params['term'] == "RNA viruses[Title]"

        # Reset the mock for the next search
        mock_get.reset_mock()
        mock_get.side_effect = [esearch_response, efetch_response, nih_response_1, nih_response_2]
        
        # Test author search
        pubmed_searcher_with_key.search("John Doe", search_type='author')
        esearch_params = mock_get.call_args_list[0][1]['params']
        assert esearch_params['term'] == "John Doe[Author]"

    @patch('time.sleep') # Mock sleep to speed up the test
    @patch('research_finder.searchers.pubmed.requests.get')
    def test_search_with_filters(self, mock_get, mock_sleep, pubmed_searcher_with_key, sample_pubmed_xml, caplog):
        """Test that date range filters are applied and citation filter is logged."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {'esearchresult': {'idlist': ['12345678', '87654321']}}
        efetch_response = MagicMock()
        efetch_response.content = sample_pubmed_xml.encode('utf-8')
        nih_response_1 = MagicMock() # Mock for the first paper's citations
        nih_response_1.json.return_value = {'data': [{'citations': 20}]}
        nih_response_2 = MagicMock() # Mock for the second paper's citations
        nih_response_2.json.return_value = {'data': [{'citations': 12}]}
        
        # Add all four mock responses to the side_effect list
        mock_get.side_effect = [esearch_response, efetch_response, nih_response_1, nih_response_2]

        filters = {'year_min': '2020', 'year_max': '2021', 'min_citations': 10}
        pubmed_searcher_with_key.search("RNA viruses", filters=filters)

        # Assert the search term includes the date range
        esearch_params = mock_get.call_args_list[0][1]['params']
        assert "AND (2020/01/01:2021/12/31[Date - Publication])" in esearch_params['term']
        
        # Assert the warning for citation filter was logged
        assert "PubMed API does not support direct citation count filtering" in caplog.text

    @patch('time.sleep') # Mock sleep to speed up the test
    @patch('research_finder.searchers.pubmed.requests.get')
    def test_fetch_citation_count_success(self, mock_get, mock_sleep, pubmed_searcher_with_key):
        """Test successful fetching of citation count from NIH iCite API."""
        nih_response = MagicMock()
        nih_response.json.return_value = {'data': [{'citations': 25}]}
        mock_get.return_value = nih_response

        count = pubmed_searcher_with_key._fetch_citation_count('12345678')
        
        assert count == 25
        mock_get.assert_called_once_with("https://icite.od.nih.gov/api/pubs?pmids=12345678", timeout=10)
        mock_sleep.assert_called_once_with(0.2)

    @patch('time.sleep')
    @patch('research_finder.searchers.pubmed.requests.get')
    def test_fetch_citation_count_failure(self, mock_get, mock_sleep, pubmed_searcher_with_key, caplog):
        """Test handling of failure when fetching citation count."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        count = pubmed_searcher_with_key._fetch_citation_count('12345678')
        
        assert count == 0
        assert "Could not fetch citation count for PMID 12345678" in caplog.text

    @patch('research_finder.searchers.pubmed.requests.get')
    def test_search_handles_no_results(self, mock_get, pubmed_searcher_with_key):
        """Test that an empty ID list from esearch is handled correctly."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {'esearchresult': {'idlist': []}}
        mock_get.return_value = esearch_response

        pubmed_searcher_with_key.search("nonexistent query")
        
        # Assert only one call (esearch) was made
        assert mock_get.call_count == 1
        assert pubmed_searcher_with_key.results == []

    @patch('research_finder.searchers.pubmed.requests.get')
    def test_search_handles_request_exception(self, mock_get, pubmed_searcher_with_key, caplog):
        """Test that a request exception during esearch is caught and logged."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        pubmed_searcher_with_key.search("bad query")

        assert pubmed_searcher_with_key.results == []
        assert "API request failed: API Error" in caplog.text

    @patch('research_finder.searchers.pubmed.requests.get')
    def test_search_handles_xml_parse_error(self, mock_get, pubmed_searcher_with_key, caplog):
        """Test that an invalid XML response from efetch is handled."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {'esearchresult': {'idlist': ['12345678']}}
        efetch_response = MagicMock()
        efetch_response.content = b"this is not valid xml"
        mock_get.side_effect = [esearch_response, efetch_response]

        pubmed_searcher_with_key.search("query")

        assert pubmed_searcher_with_key.results == []
        assert "Failed to parse PubMed XML response" in caplog.text

    def test_search_uses_cache_on_hit(self, pubmed_searcher_with_key, mock_cache_manager):
        """Test that the searcher returns cached results if they exist."""
        cached_data = [{'Title': 'Cached Paper'}]
        mock_cache_manager.get.return_value = cached_data

        pubmed_searcher_with_key.search("test query", 10)

        mock_cache_manager.get.assert_called_once()
        with patch('research_finder.searchers.pubmed.requests.get') as mock_get:
            pubmed_searcher_with_key.search("test query", 10)
            mock_get.assert_not_called()
        assert pubmed_searcher_with_key.results == cached_data

    @patch('time.sleep') # Mock sleep to speed up the test
    @patch('research_finder.searchers.pubmed.requests.get')
    def test_search_saves_to_cache_on_miss(self, mock_get, mock_sleep, pubmed_searcher_with_key, sample_pubmed_xml, mock_cache_manager):
        """Test that new results are saved to the cache after a successful search."""
        # Mock the four API calls: esearch, efetch, and two NIH iCite calls
        esearch_response = MagicMock()
        esearch_response.json.return_value = {'esearchresult': {'idlist': ['12345678', '87654321']}}
        efetch_response = MagicMock()
        efetch_response.content = sample_pubmed_xml.encode('utf-8')
        nih_response_1 = MagicMock() # Mock for the first paper's citations
        nih_response_1.json.return_value = {'data': [{'citations': 25}]}
        nih_response_2 = MagicMock() # Mock for the second paper's citations
        nih_response_2.json.return_value = {'data': [{'citations': 10}]}
        
        # Add all four mock responses to the side_effect list
        mock_get.side_effect = [esearch_response, efetch_response, nih_response_1, nih_response_2]
        mock_cache_manager.get.return_value = None

        pubmed_searcher_with_key.search("test query", 10)

        mock_cache_manager.set.assert_called_once()
        args, _ = mock_cache_manager.set.call_args
        assert len(args[3]) == 2 # The results list should have 2 papers