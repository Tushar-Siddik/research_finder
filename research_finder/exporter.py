import pandas as pd
import logging
from typing import List, Dict, Any
# UPDATED: Import the new utility function
from .utils import format_apa7

class Exporter:
    """Handles exporting data to various formats."""

    def __init__(self):
        self.logger = logging.getLogger("Exporter")

    def to_csv(self, data: List[Dict[str, Any]], filename: str) -> None:
        """Exports a list of dictionaries to a CSV file."""
        if not data:
            self.logger.warning("No data provided to export.")
            return
        
        try:
            # UPDATED: Generate APA 7 reference for each paper
            for paper in data:
                paper['APA 7 Reference'] = format_apa7(paper)

            df = pd.DataFrame(data)
            # UPDATED: Reordered columns to include new fields
            df = df[['Title', 'Authors', 'Year', 'Venue', 'Citation', 'DOI', 'URL', 'Source', 'APA 7 Reference', 'Abstract']]
            df.to_csv(filename, index=False, encoding='utf-8')
            self.logger.info(f"Successfully exported {len(data)} results to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")