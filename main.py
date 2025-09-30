import argparse
import logging
from research_finder.aggregator import Aggregator
from research_finder.exporter import Exporter
from research_finder.searchers.semantic_scholar import SemanticScholarSearcher
from research_finder.searchers.arxiv import ArxivSearcher
# from research_finder.searchers.google_scholar import GoogleScholarSearcher

def setup_logging():
    """Configure basic logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def main():
    """Main function to run the research finder tool."""
    setup_logging()
    logger = logging.getLogger("Main")

    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser(description="Find research articles from multiple sources.")
    parser.add_argument("query", type=str, help="The search query (e.g., 'quantum computing').")
    parser.add_argument("-o", "--output", type=str, default="search_results.csv", help="Output CSV filename.")
    parser.add_argument("-l", "--limit", type=int, default=10, help="Max results per source.")
    args = parser.parse_args()

    # 2. Initialize Components
    aggregator = Aggregator()
    exporter = Exporter()

    # 3. Add Searchers to the Aggregator
    # To debug a specific source, you can comment out the others.
    aggregator.add_searcher(SemanticScholarSearcher())
    aggregator.add_searcher(ArxivSearcher())
    
    # Optional: Add Google Scholar (can be unreliable)
    # try:
    #     aggregator.add_searcher(GoogleScholarSearcher())
    # except ImportError as e:
    #     logger.warning(e)

    # 4. Run Searches and Get Results
    all_articles = aggregator.run_all_searches(args.query, args.limit)

    # 5. Export Results
    if all_articles:
        exporter.to_csv(all_articles, args.output)
    else:
        logger.info("No articles found to export.")

if __name__ == "__main__":
    main()