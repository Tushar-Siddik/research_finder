import re


def format_apa7(paper: dict) -> str:
    """
    Formats a paper dictionary into a basic APA-7 style reference string.
    Note: This is an approximation and may not cover all edge cases.
    """
    # 1. Format Authors
    authors_list = [a.strip() for a in paper.get('Authors', '').split(',') if a.strip()]
    if not authors_list:
        author_str = "n.a."
    else:
        formatted_authors = []
        for author in authors_list:
            parts = author.split()
            if len(parts) == 0:
                continue
            # Assumes "Lastname Firstname" or "Lastname, F."
            last_name = parts[-1]
            initials = "".join([p[0] + "." for p in parts[:-1]])
            formatted_authors.append(f"{last_name}, {initials}")
        
        if len(formatted_authors) == 1:
            author_str = formatted_authors[0]
        elif len(formatted_authors) <= 20:
            author_str = ", ".join(formatted_authors[:-1]) + ", & " + formatted_authors[-1]
        else: # APA 7 rule for >20 authors
            author_str = formatted_authors[0] + ", et al."

    # 2. Get Year
    year = paper.get('Year', 'n.d.')
    year_str = f"({year})."

    # 3. Get Title
    title = paper.get('Title', '')
    
    # 4. Get Source/Venue and construct reference
    source = paper.get('Source')
    venue = paper.get('Venue', '')
    doi = paper.get('DOI', '')
    url = paper.get('URL', '')

    if source == 'arXiv':
        # Preprint format
        ref = f"{author_str} {year_str} *{title}* [Preprint]. arXiv."
        if url:
            ref += f" {url}"
    else:
        # Journal article format
        ref = f"{author_str} {year_str} {title}."
        if venue:
            ref += f" *{venue}*."
        
        # Add DOI or URL
        if doi:
            ref += f" https://doi.org/{doi}"
        elif url:
            ref += f" {url}"
            
    return ref.strip()

def validate_doi(doi: str) -> str:
    """
    Validates and formats a DOI to a consistent URL.
    
    Args:
        doi: The DOI string from an API, which may be in various formats.
        
    Returns:
        A full, validated DOI URL (e.g., "https://doi.org/10.1000/xyz123"), 
        or 'N/A' if the input is invalid or empty.
    """
    if not doi or not str(doi).strip() or str(doi).lower() == 'n/a':
        return 'N/A'
    
    doi_str = str(doi).strip()
    
    # A basic check for the DOI prefix (e.g., "10.1000")
    if not doi_str.startswith('10.'):
        return 'N/A'
        
    # Return the full URL
    return f"https://doi.org/{doi_str}"

def normalize_string(text: str) -> str:
    """A generic function to clean up string fields."""
    if not text or str(text).lower() == 'n/a':
        return 'N/A'
    
    # Remove extra whitespace, newlines, and tabs
    text = re.sub(r'\s+', ' ', str(text))
    return text.strip()

def normalize_authors(authors_input) -> str:
    """
    Normalizes author data from various formats into a clean string.
    
    Args:
        authors_input: Can be a list of strings, a list of dicts with a 'name' key, or a comma-separated string.
    
    Returns:
        A clean, comma-separated string of author names.
    """
    if not authors_input:
        return 'N/A'
    
    authors_list = []
    
    # Handle list of dictionaries (e.g., from Semantic Scholar)
    if isinstance(authors_input, list) and authors_input and isinstance(authors_input[0], dict):
        authors_list = [author.get('name', '').strip() for author in authors_input if author.get('name')]
    
    # Handle list of strings (e.g., from arXiv)
    elif isinstance(authors_input, list):
        authors_list = [str(author).strip() for author in authors_input if str(author).strip()]
    
    # Handle comma-separated string
    elif isinstance(authors_input, str):
        authors_list = [author.strip() for author in authors_input.split(',') if author.strip()]

    # Filter out any empty entries that might have slipped through
    clean_authors = [author for author in authors_list if author]
    
    return ', '.join(clean_authors) if clean_authors else 'N/A'

def normalize_year(year_input) -> str:
    """
    Normalizes year data from various formats into a 4-digit string.
    
    Args:
        year_input: Can be an integer, a 4-digit string, or a full date string.
    
    Returns:
        A 4-digit string or 'N/A'.
    """
    if not year_input or str(year_input).lower() == 'n/a':
        return 'N/A'
    
    # Extract just the 4-digit year if it's in a string
    match = re.search(r'\b(19|20)\d{2}\b', str(year_input))
    if match:
        return match.group(0)
    
    # If it's already a 4-digit number, return it as a string
    if str(year_input).isdigit() and len(str(year_input)) == 4:
        return str(year_input)
        
    return 'N/A'

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