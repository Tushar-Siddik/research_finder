import pandas as pd
import logging
from typing import List, Dict, Any

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
            df = pd.DataFrame(data)
            # Ensure a consistent column order
            df = df[['Title', 'Authors', 'Year', 'Source', 'URL', 'Abstract']]
            df.to_csv(filename, index=False, encoding='utf-8')
            self.logger.info(f"Successfully exported {len(data)} results to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")