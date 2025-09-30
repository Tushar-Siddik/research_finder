import pandas as pd
import logging
from typing import List, Dict, Any
from .utils import format_apa7

class Exporter:
    """Handles exporting data to various formats."""

    def __init__(self):
        self.logger = logging.getLogger("Exporter")

    def to_csv(self, data: List[Dict[str, Any]], filename: str) -> None:
        """Exports a list of dictionaries to a CSV file with a fixed set of columns."""
        if not data:
            self.logger.warning("No data provided to export.")
            return
        
        try:
            # 1. Generate APA 7 reference for each paper
            for paper in data:
                paper['APA 7 Reference'] = format_apa7(paper)

            # 2. Define the fixed, final order of columns for the output CSV
            final_columns = [
                'Title', 'Authors', 'Year', 'Venue', 'Source', 'Citation Count', 'DOI', 'License Type',
                'URL', 'APA 7 Reference'
            ]

            # 3. Create the DataFrame
            df = pd.DataFrame(data)
            
            # 4. Ensure all desired columns exist in the DataFrame before reordering
            # This prevents errors if a searcher doesn't provide a specific field
            for col in final_columns:
                if col not in df.columns:
                    df[col] = '' # Add missing columns as empty strings

            # 5. Reorder the DataFrame and save to CSV
            final_df = df[final_columns]
            final_df.to_csv(filename, index=False, encoding='utf-8')
            
            self.logger.info(f"Successfully exported {len(data)} results to {filename}")

        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")