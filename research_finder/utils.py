"""
Utility functions for data normalization, cleaning, and formatting.

This module provides a collection of helper functions used across the application,
particularly for processing data from different APIs into a standardized format.
Functions include cleaning author lists, formatting citations in APA 7 style,
and normalizing various data fields like years, DOIs, and strings.
"""

import re
import string

def clean_author_list(authors_input) -> str:
    """
    Cleans and standardizes author data into a simple, comma-separated string of full names.
    
    This function handles various input formats (list of strings, list of dictionaries,
    comma-separated string) and converts them into a uniform format.
    
    Args:
        authors_input: The author data, which can be a list, a string, or other formats.
        
    Returns:
        A comma-separated string of author names, or 'N/A' if no authors are found.
    """
    if not authors_input:
        return 'N/A'
    
    authors_list = []
    
    # Handle list of dictionaries (e.g., from Semantic Scholar API).
    if isinstance(authors_input, list) and authors_input and isinstance(authors_input[0], dict):
        authors_list = [author.get('name', '').strip() for author in authors_input if author.get('name')]
    
    # Handle list of strings (e.g., from arXiv, CrossRef APIs).
    elif isinstance(authors_input, list):
        authors_list = [str(author).strip() for author in authors_input if str(author).strip()]
    
    # Handle comma-separated string (e.g., from Google Scholar API).
    elif isinstance(authors_input, str):
        authors_list = [author.strip() for author in authors_input.split(',') if author.strip()]

    # Filter out any empty entries that might have slipped through.
    clean_authors = [author for author in authors_list if author]
    
    return ', '.join(clean_authors) if clean_authors else 'N/A'

def _to_sentence_case(text: str) -> str:
    """
    Converts a string to sentence case, following APA 7 style for article titles.
    
    Handles colons, question marks, and exclamation points by capitalizing the
    first word after each delimiter.
    
    Args:
        text: The input string.
        
    Returns:
        The sentence-cased string, or 'N/A' if the input is invalid.
    """
    if not text or text == 'N/A':
        return 'N/A'
    
    text = text.strip()
    
    # Split the title by common punctuation marks that separate clauses.
    # We use a non-capturing group (?:...) to split but keep the delimiter.
    parts = re.split(r'([:?!])', text)
    
    # Reconstruct the parts with correct capitalization.
    capitalized_parts = []
    for i in range(0, len(parts), 2): # Iterate over the text parts, not the delimiters.
        part = parts[i].strip()
        if not part:
            continue
        
        # Capitalize the first letter of the part.
        part = part[0].upper() + part[1:].lower()
        capitalized_parts.append(part)
        
        # Add the delimiter back if it exists.
        if i + 1 < len(parts):
            capitalized_parts.append(parts[i+1])
            
    return "".join(capitalized_parts)

def _to_title_case(text: str) -> str:
    """Converts a string to title case, following APA 7 style for journal titles."""
    if not text or text == 'N/A':
        return 'N/A'
    # A simple title case implementation.
    return ' '.join(word.capitalize() for word in text.strip().split())

def _parse_venue_info(venue_str: str) -> dict:
    """
    Parses a complex venue string into its components: journal, volume, issue, and pages.
    
    This function uses a flexible "extract and remove" strategy to handle various formats.
    It attempts to find pages, then issue, then volume, and treats the remaining
    text as the journal name.
    
    Args:
        venue_str: The venue string from the API.
        
    Returns:
        A dictionary with keys 'journal', 'volume', 'issue', 'pages'.
    """
    if not venue_str or venue_str == 'N/A':
        return {'journal': 'N/A', 'volume': 'N/A', 'issue': 'N/A', 'pages': 'N/A'}

    venue_str = venue_str.strip()
    
    # Initialize default values.
    journal, volume, issue, pages = 'N/A', 'N/A', 'N/A', 'N/A'
    
    # Extract pages (e.g., "408-428", "123-45", "e123").
    pages_match = re.search(r'([e]?\d+-\d+)', venue_str)
    if pages_match:
        pages = pages_match.group(1)
        venue_str = venue_str.replace(pages_match.group(0), '', 1).strip()

    # Extract issue (e.g., "(6)", ":23").
    issue_match = re.search(r'[\(,:]\s*(\d+)[\)\:]?', venue_str)
    if issue_match:
        issue = issue_match.group(1)
        venue_str = venue_str.replace(issue_match.group(0), '', 1).strip()

    # Extract volume (e.g., "13", "589").
    volume_match = re.search(r'\b(\d+)\b', venue_str)
    if volume_match:
        volume = volume_match.group(1)
        venue_str = venue_str.replace(volume_match.group(0), '', 1).strip()

    # Whatever is left is likely the journal name.
    journal = _to_title_case(venue_str.strip(' ,:'))

    return {
        'journal': journal if journal else 'N/A',
        'volume': volume,
        'issue': issue,
        'pages': pages
    }

def format_apa7(paper: dict) -> str:
    """
    Formats a paper dictionary into a robust APA-7 style reference string for a journal article.
    
    This function follows the APA 7th edition guidelines for formatting a reference,
    including author names, year, title (in sentence case), journal information, and DOI.
    
    Args:
        paper: A dictionary containing paper details (Title, Authors, Year, Venue, DOI, etc.).
        
    Returns:
        A formatted APA 7 reference string.
    """
    # 1. Format Authors
    raw_authors = paper.get('Authors', '')
    author_names = [name.strip() for name in clean_author_list(raw_authors).split(',') if name.strip()]

    if not author_names or author_names == ['N/A']:
        authors_str = "n.a."
    else:
        formatted_authors = []
        for name in author_names:
            parts = name.split()
            if not parts:
                continue
            last_name = parts[-1]
            first_middle = ' '.join(parts[:-1])
            
            initials = []
            for part in first_middle.split():
                initials.append(part[0].upper() + '.')
            
            formatted_authors.append(f"{last_name}, {' '.join(initials)}")

        # Apply APA 7 joining rules.
        num_authors = len(formatted_authors)
        if num_authors == 1:
            authors_str = formatted_authors[0]
        elif num_authors <= 20:
            authors_str = ', '.join(formatted_authors[:-1]) + ', & ' + formatted_authors[-1]
        else: # Rule for >20 authors.
            authors_str = ', '.join(formatted_authors[:19]) + ', ... ' + formatted_authors[-1]

    # 2. Format Year
    year = paper.get('Year', 'n.d.')
    year_str = f"({year})."

    # 3. Format Title (Sentence Case)
    title = _to_sentence_case(paper.get('Title', ''))
    # Only add a period if the title doesn't already end with one.
    if not title.endswith('.'):
        title_str = f"{title}."
    else:
        title_str = title

    # 4. Format Journal, Volume, Issue, Pages
    venue_info = _parse_venue_info(paper.get('Venue', ''))
    journal_str = venue_info['journal']
    volume_str = venue_info['volume']
    issue_str = venue_info['issue']
    pages_str = venue_info['pages']

    source_parts = []
    if journal_str != 'N/A':
        source_parts.append(f"*{journal_str}*") # Italicize journal name.
    if volume_str != 'N/A':
        source_parts.append(f"*{volume_str}*")   # Italicize volume.
    if issue_str != 'N/A':
        source_parts.append(f"({issue_str})")
    if pages_str != 'N/A':
        source_parts.append(pages_str)
    
    source_str = ', '.join(source_parts) + '.'

    # 5. Format DOI
    doi = paper.get('DOI', '')
    doi_str = ''
    if doi and doi != 'N/A':
        if doi.startswith('http'):
            doi_str = doi
        else:
            doi_str = f"https://doi.org/{doi}"

    # 6. Assemble the final reference.
    ref_parts = [authors_str, year_str, title_str, source_str]
    if doi_str:
        ref_parts.append(doi_str)
    
    return " ".join(ref_parts).strip()

# --- OTHER HELPER FUNCTIONS ---

def normalize_string(text: str) -> str:
    """
    Normalizes a string by stripping whitespace, common prefixes, and surrounding quotes.
    
    This function cleans up titles that may have prefixes like "Author response for"
    or be wrapped in quotation marks, which can happen with some API responses.
    
    Args:
        text: The input string.
        
    Returns:
        The cleaned and normalized string.
    """
    if not text or str(text).lower() == 'n/a':
        return 'N/A'
    
    text = str(text).strip()
    
    # Strip common prefixes from titles (e.g., "Author response for").
    prefixes_to_strip = [
        "Author response for ",
        "Correction to ",
        "Retraction of ",
        "Expression of Concern: ",
        "Reply to ",
        "Erratum for "
    ]
    for prefix in prefixes_to_strip:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()
            
    # Strip surrounding quotes (single or double).
    if (text.startswith('"') and text.endswith('"')) or \
       (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    # Replace multiple whitespace characters with a single space.
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def normalize_year(year_input) -> str:
    """
    Normalizes a year input into a standard four-digit string or 'n.d.'.
    
    Args:
        year_input: The year, which can be an int, string, or part of a larger string.
        
    Returns:
        A four-digit year string, or 'n.d.' if no valid year is found.
    """
    if not year_input or str(year_input).lower() == 'n/a':
        return 'N/A'
    # Look for a standard 4-digit year in the 20th or 21st century.
    match = re.search(r'\b(19|20)\d{2}\b', str(year_input))
    if match:
        return match.group(0)
    # Fallback for a simple 4-digit string.
    if str(year_input).isdigit() and len(str(year_input)) == 4:
        return str(year_input)
    return 'n.d.' # Use 'n.d.' for consistency.

def validate_doi(doi: str) -> str:
    """
    Validates a DOI (Digital Object Identifier) string.
    
    Args:
        doi: The DOI string to validate.
        
    Returns:
        The validated DOI string, or 'N/A' if it's invalid.
    """
    if not doi or not str(doi).strip() or str(doi).lower() == 'n/a':
        return 'N/A'
    doi_str = str(doi).strip()
    # A valid DOI must start with '10.'.
    if not doi_str.startswith('10.'):
        return 'N/A'
    return doi_str

def normalize_citation_count(count_input) -> int:
    """
    Normalizes citation count to an integer.
    
    Args:
        count_input: Can be an integer or a string containing a number.
    
    Returns:
        An integer, or 0 if the input is invalid.
    """
    if not count_input or str(count_input).lower() == 'n/a':
        return 0
    
    try:
        # Extract the first number found in the string.
        match = re.search(r'\d+', str(count_input))
        if match:
            return int(match.group(0))
    except (ValueError, TypeError):
        return 0
        
    return 0