import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# API endpoints
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_API_URL = "http://export.arxiv.org/api/query"

# Default settings
DEFAULT_RESULTS_LIMIT = 10
REQUEST_TIMEOUT = 10  # seconds
CACHE_EXPIRY_HOURS = 24

# Cache settings
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")
CACHE_EXPIRY_HOURS = 24  # Cache expires after 24 hours

# Output settings
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Environment variables
S2_API_KEY = os.getenv("S2_API_KEY", "")