"""
Pytest-style tests for the utils.py module.

This test suite verifies the correctness of utility functions for data
normalization, cleaning, and APA 7 formatting.
"""

import pytest
from research_finder.utils import (
    clean_author_list,
    _to_sentence_case,
    _to_title_case,
    _parse_venue_info,
    format_apa7,
    normalize_string,
    normalize_year,
    validate_doi,
    normalize_citation_count
)

# --- Tests for clean_author_list ---

def test_clean_author_list_empty_input():
    """Test that empty or None input returns 'N/A'."""
    assert clean_author_list(None) == 'N/A'
    assert clean_author_list([]) == 'N/A'
    assert clean_author_list('') == 'N/A'

def test_clean_author_list_list_of_dicts(sample_authors_list_dict):
    """Test handling a list of author dictionaries."""
    result = clean_author_list(sample_authors_list_dict)
    assert result == 'John Doe, Jane Smith, Peter Jones'

def test_clean_author_list_list_of_strings(sample_authors_list_string):
    """Test handling a list of author strings."""
    result = clean_author_list(sample_authors_list_string)
    assert result == 'John Doe, Jane Smith, Peter Jones, Another Author'

def test_clean_author_list_comma_separated_string(sample_authors_string_comma):
    """Test handling a comma-separated string of authors."""
    result = clean_author_list(sample_authors_string_comma)
    assert result == 'John Doe, Jane Smith, Peter Jones, Another Author'

# --- Tests for _to_sentence_case ---

def test_to_sentence_case_basic():
    assert _to_sentence_case("a simple title") == "A simple title"
    assert _to_sentence_case("A Title That Is Already Correct") == "A title that is already correct"

def test_to_sentence_case_with_punctuation():
    assert _to_sentence_case("what is a title? a question.") == "What is a title? A question."
    assert _to_sentence_case("a title: a subtitle") == "A title: A subtitle"
    assert _to_sentence_case("an amazing discovery! a new era.") == "An amazing discovery! A new era."

def test_to_sentence_case_invalid_input():
    assert _to_sentence_case(None) == 'N/A'
    assert _to_sentence_case('N/A') == 'N/A'

# --- Tests for _to_title_case ---

def test_to_title_case():
    assert _to_title_case("journal of amazing findings") == "Journal Of Amazing Findings"
    assert _to_title_case("  another journal  ") == "Another Journal"

def test_to_title_case_invalid_input():
    assert _to_title_case(None) == 'N/A'
    assert _to_title_case('N/A') == 'N/A'

# --- Tests for _parse_venue_info ---

def test_parse_venue_info_full_string():
    venue = "Journal of Testing, 13(6), 408-428"
    expected = {'journal': 'Journal Of Testing', 'volume': '13', 'issue': '6', 'pages': '408-428'}
    assert _parse_venue_info(venue) == expected

def test_parse_venue_info_no_issue():
    venue = "Journal of Testing, 13, 408-428"
    expected = {'journal': 'Journal Of Testing', 'volume': '13', 'issue': 'N/A', 'pages': '408-428'}
    assert _parse_venue_info(venue) == expected
    
def test_parse_venue_info_no_pages():
    venue = "Journal of Testing, 13(6)"
    expected = {'journal': 'Journal Of Testing', 'volume': '13', 'issue': '6', 'pages': 'N/A'}
    assert _parse_venue_info(venue) == expected

def test_parse_venue_info_invalid_input():
    assert _parse_venue_info(None) == {'journal': 'N/A', 'volume': 'N/A', 'issue': 'N/A', 'pages': 'N/A'}
    assert _parse_venue_info('N/A') == {'journal': 'N/A', 'volume': 'N/A', 'issue': 'N/A', 'pages': 'N/A'}

# --- Tests for format_apa7 ---

def test_format_apa7_standard_case(sample_paper):
    """Tests the standard APA 7 formatting with a complete paper."""
    expected = "Doe, J., & Smith, J. (2023). A Study on the Application of Unit Tests. *Journal Of Software Testing*, *15*(2), 123-145. https://doi.org/10.1234/test.2023.123"
    assert format_apa7(sample_paper) == expected

def test_format_apa7_single_author():
    """Tests APA 7 formatting with a single author."""
    paper = {
        'Title': 'a solo study',
        'Authors': 'Single Author',
        'Year': '2021',
        'Venue': 'Solo Journal, 1(1), 1-1',
        'DOI': '10.1/solo.1'
    }
    expected = "Author, S. (2021). A solo study. *Solo Journal*, *1*(1), 1-1. https://doi.org/10.1/solo.1"
    assert format_apa7(paper) == expected

def test_format_apa7_many_authors(many_authors_list):
    """Tests APA 7 formatting with more than 20 authors."""
    paper = {
        'Title': 'a massive collaboration',
        'Authors': many_authors_list,
        'Year': '2020',
        'Venue': 'Big Journal, 100(1), 1-10',
        'DOI': '10.100/big.2020.1'
    }
    expected_start = "Author 1, A., Author 2, A., Author 3, A., Author 4, A., Author 5, A., Author 6, A., Author 7, A., Author 8, A., Author 9, A., Author 10, A., Author 11, A., Author 12, A., Author 13, A., Author 14, A., Author 15, A., Author 16, A., Author 17, A., Author 18, A., Author 19, A., ... Author 22, A."
    assert format_apa7(paper).startswith(expected_start)

def test_format_apa7_missing_data():
    """Tests APA 7 formatting with missing components."""
    paper = {
        'Title': 'a study with missing data',
        'Authors': 'John Doe',
        # 'Year' is missing
        'Venue': 'Some Journal'
        # 'DOI' is missing
    }
    expected = "Doe, J. (n.d.). A study with missing data. *Some Journal*."
    assert format_apa7(paper) == expected

def test_format_apa7_title_ends_with_period():
    """Tests APA 7 formatting when the title already ends with a period."""
    paper = {
        'Title': 'A Title That Already Ends With A Period.',
        'Authors': 'John Doe',
        'Year': '2023',
        'Venue': 'Punctuation Journal, 1(1), 1-1',
        'DOI': '10.1/punc.1'
    }
    expected = "Doe, J. (2023). A Title That Already Ends With A Period. *Punctuation Journal*, *1*(1), 1-1. https://doi.org/10.1/punc.1"
    assert format_apa7(paper) == expected

def test_format_apa7_url_doi():
    """Tests APA 7 formatting with a DOI that is already a full URL."""
    paper = {
        'Title': 'a study with a url doi',
        'Authors': 'John Doe',
        'Year': '2022',
        'Venue': 'Another Journal, 10(1), 1-2',
        'DOI': 'https://doi.org/10.5678/another.2022.1'
    }
    expected = "Doe, J. (2022). A study with a url doi. *Another Journal*, *10*(1), 1-2. https://doi.org/10.5678/another.2022.1"
    assert format_apa7(paper) == expected

# --- Tests for other helper functions ---

def test_normalize_string():
    assert normalize_string("  Author response for My Title  ") == "My Title"
    assert normalize_string('"My Title"') == "My Title"
    assert normalize_string("Correction to: 'An Old Title'") == "An Old Title"
    assert normalize_string("  A   title   with   spaces  ") == "A title with spaces"
    assert normalize_string(None) == 'N/A'
    assert normalize_string('N/A') == 'N/A'

def test_normalize_year():
    assert normalize_year(2023) == "2023"
    assert normalize_year("Published in 2022") == "2022"
    assert normalize_year("some text") == "n.d."
    assert normalize_year("n.a.") == "N/A"

def test_validate_doi():
    assert validate_doi("10.1234/abcde") == "10.1234/abcde"
    assert validate_doi(" 10.1234/abcde ") == "10.1234/abcde"
    assert validate_doi("11.1234/abcde") == "N/A"
    assert validate_doi("not a doi") == "N/A"
    assert validate_doi(None) == 'N/A'

def test_normalize_citation_count():
    assert normalize_citation_count(123) == 123
    assert normalize_citation_count("Cited by 45 times") == 45
    assert normalize_citation_count("many times") == 0
    assert normalize_citation_count(None) == 0
    assert normalize_citation_count('N/A') == 0