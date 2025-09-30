import logging
from research_finder.aggregator import Aggregator
from research_finder.exporter import Exporter
from research_finder.searchers.semantic_scholar import SemanticScholarSearcher
from research_finder.searchers.arxiv import ArxivSearcher

# We will handle the optional Google Scholar import here
try:
    from research_finder.searchers.google_scholar import GoogleScholarSearcher
    GOOGLE_SCHOLAR_AVAILABLE = True
except ImportError:
    GOOGLE_SCHOLAR_AVAILABLE = False
    print("Warning: 'scholarly' library not found. Google Scholar will not be an option.")
    print("To enable it, run: pip install scholarly")


def setup_logging():
    """Configure basic logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def get_user_input():
    """Gets search parameters from the user via command-line prompts."""
    print("\n--- Research Article Finder ---")
    query = input("Enter keywords to search for: ").strip()
    if not query:
        print("Search query cannot be empty. Exiting.")
        exit()

    output_file = input("Enter output CSV filename (e.g., results.csv): ").strip()
    if not output_file:
        output_file = "search_results.csv"
    if not output_file.endswith('.csv'):
        output_file += '.csv'

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
            
    return query, output_file, limit

def get_searcher_selection():
    """
    Displays a menu of available searchers and gets the user's selection.
    """
    # Define the list of available searchers
    # Each item is a tuple: (Display Name, Searcher Class)
    available_searchers = [
        ("Semantic Scholar", SemanticScholarSearcher),
        ("arXiv", ArxivSearcher)
    ]
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

    # 1. Get user input for the search
    query, output_file, limit = get_user_input()

    # 2. Get user's choice of search vendors
    selected_searcher_classes = get_searcher_selection()

    # 3. Initialize Components
    aggregator = Aggregator()
    exporter = Exporter()

    # 4. Instantiate and add the selected searchers to the Aggregator
    for searcher_class in selected_searcher_classes:
        try:
            aggregator.add_searcher(searcher_class())
        except Exception as e:
            logger.error(f"Could not initialize searcher {searcher_class.__name__}: {e}")

    # 5. Run Searches and Get Results
    all_articles = aggregator.run_all_searches(query, limit)

    # 6. Export Results
    if all_articles:
        exporter.to_csv(all_articles, output_file)
    else:
        logger.info("No articles found to export.")

if __name__ == "__main__":
    main()