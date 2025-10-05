"""
Configuration validation module for the Research Article Finder tool.

This module provides a function to validate the application's configuration at startup.
It checks for the presence of recommended API keys and ensures that necessary directories
are accessible and writable. It separates critical errors (which should stop the application)
from warnings (which allow the application to run with limited functionality).
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Tuple

# Import configuration settings. The sys.path manipulation in main.py ensures this works.
try:
    from config import (
        S2_API_KEY, PUBMED_API_KEY, OPENALEX_EMAIL, CROSSREF_MAILTO,
        CACHE_DIR, DEFAULT_OUTPUT_DIR, PROJECT_ROOT
    )
except ImportError as e:
    # Fallback for environments where sys.path might not be set up yet.
    # This is a defensive measure; ideally, the import from above works.
    print(f"Error importing config in validator.py: {e}")
    print("Please ensure the script is run from the project root or sys.path is configured correctly.")
    # Define dummy values to prevent crashes during the import itself.
    S2_API_KEY = ""
    PUBMED_API_KEY = ""
    OPENALEX_EMAIL = ""
    CROSSREF_MAILTO = ""
    CACHE_DIR = "cache"
    DEFAULT_OUTPUT_DIR = "output"
    PROJECT_ROOT = Path(".")


def validate_config() -> Tuple[List[str], List[str]]:
    """
    Validates the application configuration against a set of requirements.

    This function checks for the presence of API keys (as warnings) and the
    accessibility/writability of essential directories (as errors).

    Returns:
        A tuple containing two lists:
        - errors (List[str]): Critical issues that should stop execution.
        - warnings (List[str]): Non-critical issues, like missing API keys.
    """
    errors = []
    warnings = []
    logger = logging.getLogger("ConfigValidator")

    # --- 1. Validate API Keys and Emails ---
    # These are warnings because the application can still function without them,
    # albeit with lower rate limits or reduced functionality.
    
    if not S2_API_KEY:
        warnings.append("Semantic Scholar API key (S2_API_KEY) not found in .env file. Rate limits will be very low.")
    
    if not PUBMED_API_KEY:
        warnings.append("PubMed API key (PUBMED_API_KEY) not found in .env file. Rate limits will be lower.")
    
    if not OPENALEX_EMAIL:
        warnings.append("OpenAlex email (OPENALEX_EMAIL) not found in .env file. Using the 'polite pool' is recommended.")
    
    if not CROSSREF_MAILTO:
        warnings.append("CrossRef email (CROSSREF_MAILTO) not found in .env file. Using the 'polite pool' is recommended.")

    # --- 2. Validate Directory Paths ---
    # These are errors because the application cannot function without a working cache
    # and output directory.

    # Cache Directory
    try:
        cache_path = Path(CACHE_DIR)
        # Resolve relative paths against the project root.
        if not cache_path.is_absolute():
            cache_path = PROJECT_ROOT / cache_path
        
        # Create the directory if it doesn't exist.
        cache_path.mkdir(parents=True, exist_ok=True)
        # Check if the directory is writable.
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