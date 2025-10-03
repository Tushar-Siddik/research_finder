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