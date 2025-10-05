import pandas as pd
import csv
import json
import logging
from typing import List, Dict, Any, Union, Iterator
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

    def to_json(self, data: Union[List[Dict[str, Any]], Iterator], filename: str) -> None:
        """Exports a list or generator of dictionaries to a JSON file."""
        if not data:
            self.logger.warning("No data provided to export.")
            return

        try:
            # Convert iterator to list if needed
            if isinstance(data, Iterator):
                data_list = list(data)
            else:
                data_list = data

            # Add APA 7 reference to each paper
            for paper in data_list:
                paper['APA 7 Reference'] = format_apa7(paper)

            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(data_list, jsonfile, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Successfully exported results to {filename}")

        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}")

    def to_bibtex(self, data: Union[List[Dict[str, Any]], Iterator], filename: str) -> None:
        """Exports a list or generator of dictionaries to a BibTeX file."""
        if not data:
            self.logger.warning("No data provided to export.")
            return

        try:
            # Convert iterator to list if needed
            if isinstance(data, Iterator):
                data_list = list(data)
            else:
                data_list = data

            with open(filename, 'w', encoding='utf-8') as bibtexfile:
                for i, paper in enumerate(data_list):
                    # Generate a citation key
                    authors = paper.get('Authors', '').split(',')[0].replace(' ', '')
                    year = paper.get('Year', 'n.d.')
                    citation_key = f"{authors}{year}" if authors != 'N/A' else f"paper{i}"
                    
                    # Write BibTeX entry
                    bibtexfile.write(f"@article{{{citation_key},\n")
                    bibtexfile.write(f"  title = {{{paper.get('Title', 'N/A')}}},\n")
                    bibtexfile.write(f"  author = {{{paper.get('Authors', 'N/A')}}},\n")
                    bibtexfile.write(f"  year = {{{paper.get('Year', 'n.d.')}}},\n")
                    bibtexfile.write(f"  journal = {{{paper.get('Venue', 'N/A')}}},\n")
                    
                    doi = paper.get('DOI', '')
                    if doi and doi != 'N/A':
                        bibtexfile.write(f"  doi = {{{doi}}},\n")
                    
                    url = paper.get('URL', '')
                    if url and url != 'N/A':
                        bibtexfile.write(f"  url = {{{url}}},\n")
                    
                    bibtexfile.write("}\n\n")
            
            self.logger.info(f"Successfully exported results to {filename}")

        except Exception as e:
            self.logger.error(f"Failed to export to BibTeX: {e}")

    def to_ris(self, data: Union[List[Dict[str, Any]], Iterator], filename: str) -> None:
        """Exports a list or generator of dictionaries to a RIS file."""
        if not data:
            self.logger.warning("No data provided to export.")
            return

        try:
            # Convert iterator to list if needed
            if isinstance(data, Iterator):
                data_list = list(data)
            else:
                data_list = data

            with open(filename, 'w', encoding='utf-8') as risfile:
                for paper in data_list:
                    # RIS type for journal articles
                    risfile.write("TY  - JOUR\n")
                    
                    # Title
                    title = paper.get('Title', 'N/A')
                    risfile.write(f"T1  - {title}\n")
                    
                    # Authors
                    authors = paper.get('Authors', '').split(',')
                    for author in authors:
                        if author.strip():
                            risfile.write(f"AU  - {author.strip()}\n")
                    
                    # Year
                    year = paper.get('Year', '')
                    if year and year != 'N/A':
                        risfile.write(f"PY  - {year}\n")
                    
                    # Journal/Venue
                    venue = paper.get('Venue', 'N/A')
                    risfile.write(f"JO  - {venue}\n")
                    
                    # DOI
                    doi = paper.get('DOI', '')
                    if doi and doi != 'N/A':
                        risfile.write(f"DO  - {doi}\n")
                    
                    # URL
                    url = paper.get('URL', '')
                    if url and url != 'N/A':
                        risfile.write(f"UR  - {url}\n")
                    
                    # End of record
                    risfile.write("ER  - \n\n")
            
            self.logger.info(f"Successfully exported results to {filename}")

        except Exception as e:
            self.logger.error(f"Failed to export to RIS: {e}")

    def to_excel(self, data: Union[List[Dict[str, Any]], Iterator], filename: str) -> None:
        """Exports a list or generator of dictionaries to an Excel file."""
        if not data:
            self.logger.warning("No data provided to export.")
            return

        # Define the final, fixed order of columns for the output Excel
        final_columns = [
            'Title', 'Authors', 'Year', 'Venue', 'Source', 
            'Citation Count', 'DOI', 'License Type', 'URL', 'APA 7 Reference'
        ]

        try:
            # Convert iterator to list if needed
            if isinstance(data, Iterator):
                data_list = list(data)
            else:
                data_list = data

            # Add APA 7 reference to each paper
            for paper in data_list:
                paper['APA 7 Reference'] = format_apa7(paper)

            df = pd.DataFrame(data_list)
            
            # Ensure all desired columns exist in the DataFrame
            for col in final_columns:
                if col not in df.columns:
                    df[col] = '' 

            final_df = df[final_columns]
            final_df.to_excel(filename, index=False, engine='openpyxl')
            
            self.logger.info(f"Successfully exported results to {filename}")

        except Exception as e:
            self.logger.error(f"Failed to export to Excel: {e}")

    def export(self, data: Union[List[Dict[str, Any]], Iterator], filename: str, format: str = 'csv') -> None:
        """
        Export data to the specified format.
        """
        format = format.lower()
        
        if not filename.endswith(f'.{format}'):
            filename = f"{filename}.{format}"
        
        self.logger.info(f"Starting export to {format.upper()} format: {filename}")
        
        # Convert iterator to list to count records
        if isinstance(data, Iterator):
            data_list = list(data)
        else:
            data_list = data

        if not data_list:
            self.logger.warning("No data provided to export.")
            return
            
        self.logger.debug(f"Preparing to export {len(data_list)} records.")
        
        if format == 'csv':
            self.to_csv(data_list, filename)
        elif format == 'json':
            self.to_json(data_list, filename)
        elif format == 'bibtex':
            self.to_bibtex(data_list, filename)
        elif format == 'ris':
            self.to_ris(data_list, filename)
        elif format in ['excel', 'xlsx']:
            self.to_excel(data_list, filename)
        else:
            self.logger.error(f"Unsupported export format: {format}")
            return

        self.logger.info(f"Successfully exported {len(data_list)} records to {filename}")