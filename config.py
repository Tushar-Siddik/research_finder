import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Semantic Scholar API settings
S2_API_KEY = os.getenv("S2_API_KEY", "")
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_RATE_LIMIT = 1.0  # 1 request per second

# ARXIV API settings
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_RATE_LIMIT = 0.5      # 2 requests per second (arXiv is more lenient)

# Google Scholar API settings

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