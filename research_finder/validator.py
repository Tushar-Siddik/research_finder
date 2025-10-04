import logging
import os
from pathlib import Path
from typing import List, Dict, Tuple

# Assuming config.py is in the parent directory of the research_finder package
# This import works because main.py adds the project root to sys.path
try:
    from config import (
        S2_API_KEY, PUBMED_API_KEY, OPENALEX_EMAIL, CROSSREF_MAILTO,
        CACHE_DIR, DEFAULT_OUTPUT_DIR, PROJECT_ROOT
    )
except ImportError as e:
    # Fallback for environments where sys.path might not be set up yet
    # This is a defensive measure, ideally the import from above works.
    print(f"Error importing config in validator.py: {e}")
    print("Please ensure the script is run from the project root or sys.path is configured correctly.")
    # Define dummy values to prevent crashes during the import itself
    S2_API_KEY = ""
    PUBMED_API_KEY = ""
    OPENALEX_EMAIL = ""
    CROSSREF_MAILTO = ""
    CACHE_DIR = "cache"
    DEFAULT_OUTPUT_DIR = "output"
    PROJECT_ROOT = Path(".")


def validate_config() -> Tuple[List[str], List[str]]:
    """
    Validates the application configuration.

    Returns:
        A tuple containing two lists:
        - A list of error messages (critical issues that should stop execution).
        - A list of warning messages (non-critical issues, like missing API keys).
    """
    errors = []
    warnings = []
    logger = logging.getLogger("ConfigValidator")

    # --- 1. Validate API Keys and Emails ---
    
    # Semantic Scholar
    if not S2_API_KEY:
        warnings.append("Semantic Scholar API key (S2_API_KEY) not found in .env file. Rate limits will be very low.")
    
    # PubMed
    if not PUBMED_API_KEY:
        warnings.append("PubMed API key (PUBMED_API_KEY) not found in .env file. Rate limits will be lower.")
    
    # OpenAlex
    if not OPENALEX_EMAIL:
        warnings.append("OpenAlex email (OPENALEX_EMAIL) not found in .env file. Using the 'polite pool' is recommended.")
    
    # CrossRef
    if not CROSSREF_MAILTO:
        warnings.append("CrossRef email (CROSSREF_MAILTO) not found in .env file. Using the 'polite pool' is recommended.")

    # --- 2. Validate Directory Paths ---

    # Cache Directory
    try:
        cache_path = Path(CACHE_DIR)
        if not cache_path.is_absolute():
            cache_path = PROJECT_ROOT / cache_path
        
        cache_path.mkdir(parents=True, exist_ok=True)
        # Check if directory is writable
        if not os.access(cache_path, os.W_OK):
            errors.append(f"Cache directory is not writable: {cache_path}")
    except Exception as e:
        errors.append(f"Could not create or access cache directory '{CACHE_DIR}': {e}")

    # Output Directory
    try:
        output_path = Path(DEFAULT_OUTPUT_DIR)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
            
        output_path.mkdir(parents=True, exist_ok=True)
        # Check if directory is writable
        if not os.access(output_path, os.W_OK):
            errors.append(f"Output directory is not writable: {output_path}")
    except Exception as e:
        errors.append(f"Could not create or access output directory '{DEFAULT_OUTPUT_DIR}': {e}")

    # --- 3. Log and Return Results ---
    
    if warnings:
        logger.warning("--- Configuration Warnings ---")
        for warning in warnings:
            logger.warning(f"  - {warning}")
        logger.warning("----------------------------")

    if errors:
        logger.error("--- Configuration Errors ---")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("---------------------------")
    
    return errors, warnings
