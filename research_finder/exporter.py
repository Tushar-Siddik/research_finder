import pandas as pd
import csv
import logging
from typing import List, Dict, Any, Union, Iterator # Add Iterator
from .utils import format_apa7

class Exporter:
    """Handles exporting data to various formats."""

    def __init__(self):
        self.logger = logging.getLogger("Exporter")

    def to_csv(self, data: Union[List[Dict[str, Any]], Iterator], filename: str) -> None:
        """Exports a list or generator of dictionaries to a CSV file."""
        if not data:
            self.logger.warning("No data provided to export.")
            return

        # Define the final, fixed order of columns for the output CSV
        final_columns = [
            'Title', 'Authors', 'Year', 'Venue', 'Source', 
            'Citation Count', 'DOI', 'License Type', 'URL', 'APA 7 Reference'
        ]

        try:
            # Check if data is a generator/iterator for streaming
            if isinstance(data, Iterator):
                self.logger.info(f"Streaming results to {filename}...")
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=final_columns)
                    writer.writeheader()
                    
                    for paper in data:
                        # Generate APA 7 reference for each paper
                        paper['APA 7 Reference'] = format_apa7(paper)
                        # Ensure all columns exist before writing
                        row_to_write = {col: paper.get(col, '') for col in final_columns}
                        writer.writerow(row_to_write)
            else:
                # Original implementation for lists
                self.logger.info(f"Loading results into memory for export to {filename}...")
                for paper in data:
                    paper['APA 7 Reference'] = format_apa7(paper)

                df = pd.DataFrame(data)
                
                # Ensure all desired columns exist in the DataFrame
                for col in final_columns:
                    if col not in df.columns:
                        df[col] = '' 

                final_df = df[final_columns]
                final_df.to_csv(filename, index=False, encoding='utf-8')
            
            self.logger.info(f"Successfully exported results to {filename}")

        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")