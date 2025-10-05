import argparse
import logging
from research_finder.aggregator import Aggregator
from research_finder.exporter import Exporter
from research_finder.searchers.semantic_scholar import SemanticScholarSearcher
from research_finder.searchers.arxiv import ArxivSearcher
from research_finder.searchers.pubmed import PubmedSearcher
from research_finder.searchers.crossref import CrossrefSearcher
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE
# --- IMPORT THE VALIDATOR ---
from research_finder.validator import validate_config

# We will handle the optional Google Scholar import here
try:
    from research_finder.searchers.google_scholar import GoogleScholarSearcher
    GOOGLE_SCHOLAR_AVAILABLE = True
except ImportError:
    GOOGLE_SCHOLAR_AVAILABLE = False
    print("Warning: 'scholarly' library not found. Google Scholar will not be an option.")
    print("To enable it, run: pip install scholarly")

try:
    from research_finder.searchers.openalex import OpenAlexSearcher
    PYALEX_AVAILABLE = True
except ImportError:
    PYALEX_AVAILABLE = False
    print("Warning: 'pyalex' library not found. OpenAlex will not be an option.")
    print("To enable it, run: pip install pyalex")


def setup_logging():
    """Configure basic logging for the application."""
    handlers = [logging.StreamHandler()]
    
    if LOG_FILE:
        try:
            file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8')
            handlers.append(file_handler)
            print(f"Logging to file: {LOG_FILE}")
        except Exception as e:
            print(f"Warning: Could not set up log file. Error: {e}")

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=handlers
    )

def get_user_input():
    """Gets search parameters from the user via command-line prompts."""
    print("\n--- Research Article Finder ---")
    query = input("Enter keywords to search for: ").strip()
    if not query:
        print("Search query cannot be empty. Exiting.")
        exit()

    output_file = input("Enter output filename (without extension): ").strip()
    if not output_file:
        output_file = f"{query}_search_results"
    
    # Get export format
    print("\n--- Select Export Format ---")
    print("1. CSV")
    print("2. JSON")
    print("3. BibTeX")
    print("4. RIS")
    print("5. Excel")
    
    format_map = {
        "1": "csv",
        "2": "json",
        "3": "bibtex",
        "4": "ris",
        "5": "excel"
    }
    
    while True:
        format_choice = input("Select export format (1-5, default=1): ").strip()
        if not format_choice:
            format_choice = "1"
            
        if format_choice in format_map:
            export_format = format_map[format_choice]
            break
        else:
            print("Invalid option. Please enter 1, 2, 3, 4, or 5.")

    while True:
        try:
            limit_str = input("Enter max results per source (e.g., 10): ").strip()
            limit = int(limit_str)
            if limit > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    # Improved cache management options
    print("\n--- Cache Management ---")
    print("1. Don't clear cache (use existing cached results)")
    print("2. Clear only expired cache entries")
    print("3. Clear all cache entries")
    
    while True:
        cache_option = input("Select cache option (1-3, default=1): ").strip()
        if not cache_option:
            cache_option = "1"
            
        if cache_option in ["1", "2", "3"]:
            break
        else:
            print("Invalid option. Please enter 1, 2, or 3.")
    
    # Convert to boolean flags for backward compatibility
    clear_cache = (cache_option == "3")
    clear_expired = (cache_option == "2")
            
    return query, output_file, limit, clear_cache, clear_expired, export_format

def get_searcher_selection():
    """
    Displays a menu of available searchers and gets the user's selection.
    """
    # Define the list of available searchers
    # Each item is a tuple: (Display Name, Searcher Class)
    available_searchers = [
        ("Semantic Scholar", SemanticScholarSearcher),
        ("arXiv", ArxivSearcher),
        ("PubMed", PubmedSearcher),
        ("CrossRef", CrossrefSearcher)
    ]
    if PYALEX_AVAILABLE:
        available_searchers.append(("OpenAlex", OpenAlexSearcher))
    if GOOGLE_SCHOLAR_AVAILABLE:
        available_searchers.append(("Google Scholar (Unreliable)", GoogleScholarSearcher))

    print("\n--- Select Search Vendors ---")
    for i, (name, _) in enumerate(available_searchers, 1):
        print(f"  {i}. {name}")
    
    while True:
        choice_str = input(f"Enter vendor numbers to use (e.g., 1,2) or press Enter for all: ").strip()
        
        # If user presses Enter, select all
        if not choice_str:
            return [searcher_class for (_, searcher_class) in available_searchers]

        try:
            # Parse comma-separated numbers
            chosen_indices = [int(num.strip()) for num in choice_str.split(',')]
            selected_searchers = []
            
            # Validate choices
            for index in chosen_indices:
                if 1 <= index <= len(available_searchers):
                    selected_searchers.append(available_searchers[index - 1][1])
                else:
                    raise ValueError(f"Invalid number: {index}")
            
            if not selected_searchers:
                print("No valid vendors selected. Please try again.")
                continue

            return selected_searchers

        except (ValueError, IndexError):
            print("Invalid input. Please enter numbers separated by commas (e.g., 1,3).")

def main():
    """Main function to run the research finder tool."""
    setup_logging()
    logger = logging.getLogger("Main")

    # --- VALIDATE CONFIGURATION AT STARTUP ---
    errors, warnings = validate_config()
    if errors:
        print("\nConfiguration validation failed with critical errors. Please address them and restart.")
        sys.exit(1) # Exit with a non-zero status code to indicate an error
    
    if warnings:
        print("\nConfiguration validation completed with warnings. The tool will run with limited functionality.")
        print("See the logs above for details. Press Enter to continue.")
        input() # Pause for user to acknowledge warnings
    else:
        print("\nConfiguration validation successful. All settings are OK.")

    # 1. Get user input for the search
    query, output_file, limit, clear_cache, _, export_format = get_user_input()
    
    # --- NEW: Log user configuration for debugging ---
    logger.debug(f"User input received - Query: '{query}', Limit: {limit}, Format: {export_format}, Output: {output_file}")
    # --- END OF NEW SECTION ---

    # 2. Get user's choice of search vendors
    selected_searcher_classes = get_searcher_selection()
    logger.debug(f"Selected searchers: {[cls.__name__ for cls in selected_searcher_classes]}")

    # 3. Initialize Components
    aggregator = Aggregator()
    exporter = Exporter()
    
    # 4. Handle cache clearing if requested
    if clear_cache:
        aggregator.clear_cache()
        logger.info("All cache cleared.")
    else:
        aggregator.clear_expired_cache()
        logger.info("Expired cache entries cleared.")

    # 5. Instantiate and add the selected searchers to the Aggregator
    for searcher_class in selected_searcher_classes:
        try:
            searcher = searcher_class(cache_manager=aggregator.cache_manager)
            aggregator.add_searcher(searcher)
        except ImportError as e:
            logger.error(f"Could not initialize searcher {searcher_class.__name__}: {e}")
        except Exception as e:
            logger.error(f"Could not initialize searcher {searcher_class.__name__}: {e}")

    # 6. Run Searches and Get Results
    all_articles = aggregator.run_all_searches(query, limit, stream=True)

    # 7. Export Results
    if all_articles:
        exporter.export(all_articles, output_file, export_format)
    else:
        logger.info("No articles found to export.")

    # 8. Display the Error Recovery Summary
    print("\n--- Search Summary ---")
    summary = aggregator.get_last_run_summary()
    
    if summary['successful']:
        print(f"Successfully searched: {', '.join(summary['successful'])}")
    
    if summary['failed']:
        print(f"Failed to search: {', '.join(summary['failed'])}")
        print("Please check your API keys or network connection for the failed sources.")
        
    print("----------------------\n")
        
if __name__ == "__main__":
    main()