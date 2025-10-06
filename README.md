# Research Article Finder

A comprehensive Python tool for searching research articles across multiple academic databases with advanced filtering, deduplication, and export capabilities.

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

## Features

- **Multi-Source Search**: Query multiple academic databases simultaneously:
  - Semantic Scholar
  - arXiv
  - PubMed
  - CrossRef
  - OpenAlex
  - Google Scholar (unofficial, use with caution)

- **Flexible Search Options**:
  - Search by keywords, title, or author
  - Apply filters for publication year range and citation count
  - Configurable result limits per source

- **Smart Caching**: 
  - Avoid repeated API calls with intelligent caching
  - Configurable cache expiry times
  - Options to clear all or expired cache entries

- **Deduplication**: 
  - Automatic removal of duplicate articles based on DOI and title
  - Preserves the most complete record for each unique article

- **Export Capabilities**:
  - CSV, JSON, BibTeX, RIS, and Excel formats
  - APA 7 formatted references for all articles
  - Customizable output filenames

- **Rate Limiting**: 
  - Respectful API usage with configurable rate limits
  - Enhanced limits when API keys are provided

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/research-finder.git
cd research-finder
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your API keys (optional but recommended):
```
# Semantic Scholar API Key (for higher rate limits)
S2_API_KEY=your_semantic_scholar_api_key

# PubMed API Key (for higher rate limits)
PUBMED_API_KEY=your_pubmed_api_key

# OpenAlex Email (for 'polite pool' access)
OPENALEX_EMAIL=your_email@example.com

# CrossRef Email (for 'polite pool' access)
CROSSREF_MAILTO=your_email@example.com

# Optional: Log file path
LOG_FILE=research_finder.log
```

## Usage

Run the tool from the command line:

```bash
python main.py
```

Follow the interactive prompts to:
1. Select search type (keywords, title, or author)
2. Enter your search query
3. Set result limits
4. Configure cache management
5. Apply optional filters
6. Select which databases to search
7. Choose export format and filename

### Example Workflow

```
--- Research Article Finder ---
What would you like to search by?
1. Keywords (in title, abstract, etc.)
2. Title
3. Author
Select search type (1-3, default=1): 1
Enter keywords to search for: machine learning in healthcare
Enter max results per source (e.g., 10): 20

--- Cache Management ---
1. Don't clear cache (use existing cached results)
2. Clear only expired cache entries
3. Clear all cache entries
Select cache option (1-3, default=1): 2

--- Filter Search Results (Optional) ---
Would you like to apply any filters to the search results? (y/n, default=n): y
--- Set Filter Criteria ---
Filter by publication year? (y/n, default=n): y
Enter start year (e.g., 2020, leave blank for no limit): 2020
Enter end year (e.g., 2023, leave blank for no limit): 2023
Filter by minimum citation count? (y/n, default=n): y
Enter minimum citation count (e.g., 50): 50

--- Select Search Vendors ---
1. Semantic Scholar
2. arXiv
3. PubMed
4. CrossRef
5. OpenAlex
6. Google Scholar (Unreliable)
Enter vendor numbers to use (e.g., 1,2) or press Enter for all: 1,3,5

--- Search Summary ---
Successfully searched: Semantic Scholar, PubMed, OpenAlex
Found 45 unique articles.

Would you like to export these results? (y/n): y
--- Select Export Format ---
1. CSV
2. JSON
3. BibTeX
4. RIS
5. Excel
Select export format (1-5, default=1): 1
Enter output filename (without extension): ml_healthcare_2020_2023
```

## Project Structure

```
research_finder/
├── cache/                  # Cache storage directory
├── output/                 # Exported files directory
├── research_finder/        # Main package
│   ├── __init__.py
│   ├── aggregator.py       # Coordinates searches across sources
│   ├── cache.py            # Caching functionality
│   ├── exporter.py         # Export functionality
│   ├── utils.py            # Utility functions
│   ├── validator.py        # Configuration validation
│   └── searchers/          # Database-specific searchers
│       ├── __init__.py
│       ├── arxiv.py
│       ├── base_searcher.py
│       ├── crossref.py
│       ├── google_scholar.py
│       ├── openalex.py
│       ├── pubmed.py
│       └── semantic_scholar.py
├── tests/                  # Test suite
├── config.py               # Configuration settings
├── LICENSE                 # MIT License
├── main.py                 # Main entry point
├── README.md               # This file
└── requirements.txt        # Dependencies
```

## API Keys and Rate Limits

While the tool works without API keys, providing them enables higher rate limits:

| Source | API Key/Email | Rate Limit with Key | Rate Limit without Key |
|--------|---------------|---------------------|------------------------|
| Semantic Scholar | S2_API_KEY | 1 req/sec | 1 req/10 sec |
| PubMed | PUBMED_API_KEY | 10 req/sec | 3 req/sec |
| OpenAlex | OPENALEX_EMAIL | 10 req/sec | 2 req/sec |
| CrossRef | CROSSREF_MAILTO | 1 req/sec | 1 req/2 sec |
| arXiv | Not required | 2 req/sec | 2 req/sec |
| Google Scholar | Not available | 1 req/5 sec | 1 req/5 sec |

## Testing

Run the test suite:

```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

When adding a new searcher:
1. Inherit from `BaseSearcher` in `research_finder/searchers/base_searcher.py`
2. Implement the required `search` method
3. Add tests in the `tests/test_searchers` directory
4. Update documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

- Google Scholar has no official API, and the scraper is unreliable and may be blocked. Use with caution.
- Always respect the terms of service of the APIs you are using.
- Citation counts may vary between sources as they are calculated differently.

## Acknowledgments

- [Semantic Scholar Academic Graph API](https://www.semanticscholar.org/product/api)
- [arXiv API](https://arxiv.org/help/api)
- [NCBI Entrez APIs](https://www.ncbi.nlm.nih.gov/home/develop/api/)
- [CrossRef REST API](https://www.crossref.org/services/api/)
- [OpenAlex](https://openalex.org/)
- [scholarly](https://github.com/scholarly-python-package/scholarly) for Google Scholar access