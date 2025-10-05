"""
Main entry point for the Research Article Finder tool.

This script orchestrates the entire search process:
1. Validates the application configuration.
2. Gathers search parameters (query, type, filters, vendors) from the user.
3. Initializes and runs searches across multiple academic databases.
4. Aggregates and de-duplicates the results.
5. Provides an option to export the final results in various formats.
"""

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
from research_finder.validator import validate_config
from typing import Dict, Any

# Handle optional imports for searchers that may not have their dependencies installed.
# This allows the tool to run with a subset of searchers if some packages are missing.
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
    """Configures basic logging for the application.
    
    Sets up logging to output to the console. If a LOG_FILE is specified
    in the configuration, it also adds a file handler to log to a file.
    """
    handlers = [logging.StreamHandler()]
    
    # Add a file handler if LOG_FILE is set in the environment variables.
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
    """Collects all necessary search parameters from the user via command-line prompts.
    
    This function guides the user through a series of questions to define the search query,
    the type of search, the maximum number of results, and cache management options.
    
    Returns:
        A tuple containing:
        - query (str): The search term.
        - limit (int): The maximum number of results per source.
        - clear_cache (bool): Whether to clear all cache.
        - clear_expired (bool): Whether to clear only expired cache.
        - search_type (str): The type of search ('keyword', 'title', or 'author').
    """
    print("\n--- Research Article Finder ---")
    
    # --- Step 1: Get Search Type ---
    print("What would you like to search by?")
    print("1. Keywords (in title, abstract, etc.)")
    print("2. Title")
    print("3. Author")
    
    search_type_map = {"1": "keyword", "2": "title", "3": "author"}
    
    while True:
        type_choice = input("Select search type (1-3, default=1): ").strip()
        if not type_choice:
            type_choice = "1"
        if type_choice in search_type_map:
            search_type = search_type_map[type_choice]
            break
        else:
            print("Invalid option. Please enter 1, 2, or 3.")

    # --- Step 2: Get Search Query ---
    prompt_text = f"Enter {search_type} to search for: "
    query = input(prompt_text).strip()
    if not query:
        print(f"Search {search_type} cannot be empty. Exiting.")
        exit()
    
    # --- Step 3: Get Result Limit ---
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
    
    # --- Step 4: Get Cache Management Option ---
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
    
    # Convert the user's choice into boolean flags for later use.
    clear_cache = (cache_option == "3")
    clear_expired = (cache_option == "2")
            
    return query, limit, clear_cache, clear_expired, search_type

def get_filter_options() -> Dict[str, Any]:
    """Prompts the user to set optional filters for the search results.
    
    Returns:
        A dictionary containing the chosen filters, e.g., {'year_min': 2020}.
        Returns an empty dict if no filters are selected.
    """
    print("\n--- Filter Search Results (Optional) ---")
    print("Would you like to apply any filters to the search results?")
    
    while True:
        choice = input("Apply filters? (y/n, default=n): ").strip().lower()
        if choice in ['y', 'yes']:
            filters = {}
            print("\n--- Set Filter Criteria ---")
            
            # --- Year Range Filter ---
            while True:
                year_choice = input("Filter by publication year? (y/n, default=n): ").strip().lower()
                if year_choice in ['y', 'yes']:
                    while True:
                        try:
                            year_min = input("Enter start year (e.g., 2020, leave blank for no limit): ").strip()
                            year_max = input("Enter end year (e.g., 2023, leave blank for no limit): ").strip()
                            
                            filters['year_min'] = int(year_min) if year_min else None
                            filters['year_max'] = int(year_max) if year_max else None
                            
                            if filters['year_min'] and filters['year_max'] and filters['year_min'] > filters['year_max']:
                                print("Start year cannot be after end year. Please try again.")
                                continue
                            break
                        except ValueError:
                            print("Invalid input. Please enter a valid year.")
                    break
                elif year_choice in ['n', 'no', '']:
                    break
                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

            # --- Citation Count Filter ---
            while True:
                citation_choice = input("Filter by minimum citation count? (y/n, default=n): ").strip().lower()
                if citation_choice in ['y', 'yes']:
                    while True:
                        try:
                            min_citations = input("Enter minimum citation count (e.g., 50): ").strip()
                            if min_citations:
                                filters['min_citations'] = int(min_citations)
                                break
                            else:
                                print("Citation count cannot be empty for this filter.")
                        except ValueError:
                            print("Invalid input. Please enter a number.")
                    break
                elif citation_choice in ['n', 'no', '']:
                    break
                else:
                    print("Invalid input. Please enter 'y' or 'n'.")
            
            return filters

        elif choice in ['n', 'no', '']:
            return {} # Return empty dict if no filters are chosen
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


def get_searcher_selection():
    """Displays a menu of available searchers and gets the user's selection.
    
    Returns:
        A list of searcher classes selected by the user.
    """
    # Define the list of available searchers.
    # Each item is a tuple: (Display Name, Searcher Class)
    available_searchers = [
        ("Semantic Scholar", SemanticScholarSearcher),
        ("arXiv", ArxivSearcher),
        ("PubMed", PubmedSearcher),
        ("CrossRef", CrossrefSearcher)
    ]
    # Add optional searchers to the list if their dependencies are available.
    if PYALEX_AVAILABLE:
        available_searchers.append(("OpenAlex", OpenAlexSearcher))
    if GOOGLE_SCHOLAR_AVAILABLE:
        available_searchers.append(("Google Scholar (Unreliable)", GoogleScholarSearcher))

    print("\n--- Select Search Vendors ---")
    for i, (name, _) in enumerate(available_searchers, 1):
        print(f"  {i}. {name}")
    
    while True:
        choice_str = input(f"Enter vendor numbers to use (e.g., 1,2) or press Enter for all: ").strip()
        
        # If user presses Enter, select all available searchers.
        if not choice_str:
            return [searcher_class for (_, searcher_class) in available_searchers]

        try:
            # Parse comma-separated numbers into a list of integers.
            chosen_indices = [int(num.strip()) for num in choice_str.split(',')]
            selected_searchers = []
            
            # Validate choices and map them to searcher classes.
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
    # This ensures all necessary settings and directories are in place before proceeding.
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

    # --- GATHER USER INPUT ---
    # 1. Get core search parameters.
    query, limit, clear_cache, _, search_type = get_user_input()
    
    # 2. Get optional filter criteria.
    filters = get_filter_options()
    logger.debug(f"User input received - Type: {search_type}, Query: '{query}', Limit: {limit}, Filters: {filters}")

    # 3. Get user's choice of search vendors.
    selected_searcher_classes = get_searcher_selection()
    logger.debug(f"Selected searchers: {[cls.__name__ for cls in selected_searcher_classes]}")

    # --- INITIALIZE CORE COMPONENTS ---
    aggregator = Aggregator()
    exporter = Exporter()
    
    # --- HANDLE CACHE ---
    # 4. Handle cache clearing based on user's choice.
    if clear_cache:
        aggregator.clear_cache()
        logger.info("All cache cleared.")
    else:
        aggregator.clear_expired_cache()
        logger.info("Expired cache entries cleared.")

    # --- SETUP SEARCHERS ---
    # 5. Instantiate and add the selected searchers to the Aggregator.
    for searcher_class in selected_searcher_classes:
        try:
            searcher = searcher_class(cache_manager=aggregator.cache_manager)
            aggregator.add_searcher(searcher)
        except ImportError as e:
            logger.error(f"Could not initialize searcher {searcher_class.__name__}: {e}")
        except Exception as e:
            logger.error(f"Could not initialize searcher {searcher_class.__name__}: {e}")

    # --- EXECUTE SEARCH ---
    # 6. Run searches across all selected vendors and aggregate the results.
    all_articles = list(aggregator.run_all_searches(query, limit, search_type, filters=filters, stream=True))

    # --- DISPLAY SUMMARY ---
    # 7. Display a summary of which searches succeeded or failed.
    print("\n--- Search Summary ---")
    summary = aggregator.get_last_run_summary()
    
    if summary['successful']:
        print(f"Successfully searched: {', '.join(summary['successful'])}")
    
    if summary['failed']:
        print(f"Failed to search: {', '.join(summary['failed'])}")
        print("Please check your API keys or network connection for the failed sources.")
        
    print("----------------------\n")

    # --- POST-SEARCH EXPORT ---
    # 8. Handle the post-search export logic.
    if not all_articles:
        logger.info("No articles found to export.")
        print("No articles found matching your criteria.")
        return

    print(f"Found {len(all_articles)} unique articles.")
    
    while True:
        export_choice = input("Would you like to export these results? (y/n): ").strip().lower()
        if export_choice in ['y', 'yes']:
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

            # Get output filename
            output_file = input("Enter output filename (without extension): ").strip()
            if not output_file:
                output_file = f"{query}_search_results"
            
            # Export Results
            exporter.export(all_articles, output_file, export_format)
            break # Exit the loop after successful export

        elif export_choice in ['n', 'no']:
            print("Exiting without exporting.")
            break # Exit the loop
        else:
            print("Invalid input. Please enter 'y' or 'n'.")
        
if __name__ == "__main__":
    main()