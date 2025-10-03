import re
import string

def clean_author_list(authors_input) -> str:
    """
    Cleans author data into a simple, comma-separated string of full names.
    This is for the 'Authors' column in the CSV.
    """
    if not authors_input:
        return 'N/A'
    
    authors_list = []
    
    # Handle list of dictionaries (e.g., from Semantic Scholar)
    if isinstance(authors_input, list) and authors_input and isinstance(authors_input[0], dict):
        authors_list = [author.get('name', '').strip() for author in authors_input if author.get('name')]
    
    # Handle list of strings (e.g., from arXiv, CrossRef)
    elif isinstance(authors_input, list):
        # BUG FIX: Changed 'authors_list' to 'authors_input' in the loop
        authors_list = [str(author).strip() for author in authors_input if str(author).strip()]
    
    # Handle comma-separated string (e.g., from Google Scholar)
    elif isinstance(authors_input, str):
        authors_list = [author.strip() for author in authors_input.split(',') if author.strip()]

    # Filter out any empty entries that might have slipped through
    clean_authors = [author for author in authors_list if author]
    
    return ', '.join(clean_authors) if clean_authors else 'N/A'

def _to_sentence_case(text: str) -> str:
    """
    Converts a string to sentence case (APA 7 style for article titles).
    Handles colons, question marks, and exclamation points.
    """
    if not text or text == 'N/A':
        return 'N/A'
    
    text = text.strip()
    
    # Split the title by common punctuation marks that separate clauses
    # We use a non-capturing group (?:...) to split but keep the delimiter
    parts = re.split(r'([:?!])', text)
    
    # Reconstruct the parts with correct capitalization
    capitalized_parts = []
    for i in range(0, len(parts), 2): # Iterate over the text parts, not the delimiters
        part = parts[i].strip()
        if not part:
            continue
        
        # Capitalize the first letter of the part
        part = part[0].upper() + part[1:].lower()
        capitalized_parts.append(part)
        
        # Add the delimiter back if it exists
        if i + 1 < len(parts):
            capitalized_parts.append(parts[i+1])
            
    return "".join(capitalized_parts)

def _to_title_case(text: str) -> str:
    """Converts a string to title case (APA 7 style for journal titles)."""
    if not text or text == 'N/A':
        return 'N/A'
    # A simple title case implementation
    return ' '.join(word.capitalize() for word in text.strip().split())

def _parse_venue_info(venue_str: str) -> dict:
    """
    Tries to parse a complex venue string into journal, volume, issue, and pages.
    
    NOTE: This is a best-effort parser using a regular expression to handle common formats.
    It may not successfully parse every possible venue string format from all APIs.
    Example input: "Psycho-Oncology, 13(6), 408-428"
    """
    if not venue_str or venue_str == 'N/A':
        return {'journal': 'N/A', 'volume': 'N/A', 'issue': 'N/A', 'pages': 'N/A'}

    # Regex to capture journal, volume, issue, and pages
    # This is a best-effort attempt and may not work for all formats
    match = re.match(r'^(.*?),\s*([0-9]+)\(([^)]+)\),?\s*(.*)$', venue_str)
    if match:
        return {
            'journal': _to_title_case(match.group(1)),
            'volume': match.group(2),
            'issue': match.group(3),
            'pages': match.group(4) or 'N/A'
        }
    
    # Fallback if regex fails (e.g., no issue or pages)
    match_simple = re.match(r'^(.*?),\s*([0-9]+)', venue_str)
    if match_simple:
        return {
            'journal': _to_title_case(match_simple.group(1)),
            'volume': match_simple.group(2),
            'issue': 'N/A',
            'pages': 'N/A'
        }

    # Final fallback: treat the whole string as the journal name
    return {'journal': _to_title_case(venue_str), 'volume': 'N/A', 'issue': 'N/A', 'pages': 'N/A'}

def format_apa7(paper: dict) -> str:
    """
    Formats a paper dictionary into a robust APA-7 style reference string for a journal article.
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

        # Apply APA 7 joining rules
        num_authors = len(formatted_authors)
        if num_authors == 1:
            authors_str = formatted_authors[0]
        elif num_authors <= 20:
            authors_str = ', '.join(formatted_authors[:-1]) + ', & ' + formatted_authors[-1]
        else: # Rule for >20 authors
            authors_str = ', '.join(formatted_authors[:19]) + ', ... ' + formatted_authors[-1]

    # 2. Format Year
    year = paper.get('Year', 'n.d.')
    year_str = f"({year})."

    # 3. Format Title (Sentence Case)
    title = _to_sentence_case(paper.get('Title', ''))
    # Only add a period if the title doesn't already end with one
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
        source_parts.append(f"*{journal_str}*")
    if volume_str != 'N/A':
        source_parts.append(f"*{volume_str}*")
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

    # 6. Assemble the final reference
    ref_parts = [authors_str, year_str, title_str, source_str]
    if doi_str:
        ref_parts.append(doi_str)
    
    return " ".join(ref_parts).strip()

# --- Keep other helper functions ---
def normalize_string(text: str) -> str:
    if not text or str(text).lower() == 'n/a':
        return 'N/A'
    text = re.sub(r'\s+', ' ', str(text))
    return text.strip()

def normalize_year(year_input) -> str:
    if not year_input or str(year_input).lower() == 'n/a':
        return 'N/A'
    match = re.search(r'\b(19|20)\d{2}\b', str(year_input))
    if match:
        return match.group(0)
    if str(year_input).isdigit() and len(str(year_input)) == 4:
        return str(year_input)
    return 'n.d.' # Use 'n.d.' for consistency

def validate_doi(doi: str) -> str:
    if not doi or not str(doi).strip() or str(doi).lower() == 'n/a':
        return 'N/A'
    doi_str = str(doi).strip()
    if not doi_str.startswith('10.'):
        return 'N/A'
    return doi_str

def normalize_citation_count(count_input) -> int:
    """
    Normalizes citation count to an integer.
    
    Args:
        count_input: Can be an integer or a string.
    
    Returns:
        An integer, or 0 if the input is invalid.
    """
    if not count_input or str(count_input).lower() == 'n/a':
        return 0
    
    try:
        # Extract the first number found in the string
        match = re.search(r'\d+', str(count_input))
        if match:
            return int(match.group(0))
    except (ValueError, TypeError):
        return 0
        
    return 0