"""
Central configuration file for the Research Article Finder tool.

This script loads settings from environment variables (defined in a .env file)
and provides them as constants for use throughout the application. It also defines
default values and other static settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from a .env file, if it exists.
# This keeps sensitive data like API keys out of the source code.
load_dotenv()

# Get the absolute path to the project's root directory.
# This is used to resolve relative paths for cache and output directories.
PROJECT_ROOT = Path(__file__).parent.absolute()

# --- API CONFIGURATION ---
# Settings for the various academic database APIs.

# Semantic Scholar API
S2_API_KEY = os.getenv("S2_API_KEY", "")  # API key for higher rate limits.
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_RATE_LIMIT_WITH_KEY = 1.0  # 1 request per second with key.
SEMANTIC_SCHOLAR_RATE_LIMIT_NO_KEY = 0.1    # 1 request per 10 seconds without key.

# arXiv API
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_RATE_LIMIT = 0.5      # 2 requests per second (arXiv is more lenient).

# Google Scholar (via 'scholarly' library)
GOOGLE_SCHOLAR_RATE_LIMIT = 5.0    # 1 request every 5 seconds (be very careful to avoid being blocked).

# PubMed (Entrez) API
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")  # API key for higher rate limits.
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_RATE_LIMIT_WITH_KEY = 0.1   # 10 requests per second with API key.
PUBMED_RATE_LIMIT_NO_KEY = 0.33    # 3 requests per second without API key.

# OpenAlex API (via 'pyalex' library)
# We are using the pyalex Python package: https://github.com/J535D165/pyalex
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")  # Email for 'polite pool' access.
OPENALEX_RATE_LIMIT_WITH_EMAIL = 0.1 # 10 requests per second with email.
OPENALEX_RATE_LIMIT_NO_EMAIL = 0.5  # 2 requests per second without email.

# CrossRef API
CROSSREF_API_URL = "https://api.crossref.org/works"
CROSSREF_RATE_LIMIT_WITH_KEY = 1.0  # 1 request per second (be polite).
CROSSREF_RATE_LIMIT_NO_KEY = 2.0    # 1 request per 2 seconds (be polite).
CROSSREF_MAILTO = os.getenv("CROSSREF_MAILTO", "")  # Email for polite pool.

# --- DEFAULT APPLICATION SETTINGS ---

# The default number of results to fetch from each source if not specified by the user.
DEFAULT_RESULTS_LIMIT = 10

# The timeout in seconds for any network request made by the tool.
REQUEST_TIMEOUT = 10

# The default time-to-live for cache entries, in hours.
CACHE_EXPIRY_HOURS = 24

# --- DIRECTORY SETTINGS ---

# The directory where cache files will be stored.
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")

# The default directory where output files will be saved.
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# --- LOGGING SETTINGS ---

# The logging level for the application. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL.
LOG_LEVEL = "INFO"

# The format for log messages.
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Set to a filename to enable logging to a file. If empty, logs only to the console.
# Can be set via an environment variable, e.g., LOG_FILE="research_finder.log"
LOG_FILE = os.getenv("LOG_FILE", "")