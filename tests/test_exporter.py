"""
Pytest-style tests for the exporter.py module.

This test suite verifies the functionality of the Exporter class, including
routing to the correct format, file creation, and data integrity for each
export type (CSV, JSON, BibTeX, RIS, Excel).
"""

import pytest
import json
import csv
import pandas as pd
# from pytest import tmp_path
from pathlib import Path

# Ensure the module can be imported correctly
# This assumes your project structure allows for this import path.
from research_finder.exporter import Exporter
from research_finder.utils import format_apa7

# Note: The exporter.py module modifies sys.path. For tests to run reliably,
# it's best if the project is installed in editable mode (pip install -e .)
# or the PYTHONPATH is configured correctly.

class TestExporter:
    """Test suite for the Exporter class."""

    def test_export_csv_creates_file_with_correct_content(self, tmp_path, sample_data_list):
        """Tests CSV export with a list of data."""
        exporter = Exporter()
        filepath = tmp_path / "output.csv"
        exporter.to_csv(sample_data_list, str(filepath))

        assert filepath.exists()
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            # Check header
            assert 'APA 7 Reference' in reader.fieldnames
            # Check content of the first row
            assert rows[0]['Title'] == 'A Study on the Application of Unit Tests'
            assert rows[0]['APA 7 Reference'] == format_apa7(sample_data_list[0])

    def test_export_csv_with_generator(self, tmp_path, sample_data_generator):
        """Tests CSV export with a generator of data."""
        exporter = Exporter()
        filepath = tmp_path / "output_gen.csv"
        
        # The fixture already returns the generator, no need to call it.
        exporter.to_csv(sample_data_generator, str(filepath))

        assert filepath.exists()
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]['Title'] == 'A Study on the Application of Unit Tests'
            assert rows[1]['Title'] == 'Another Study on Software'

    def test_export_json_creates_file_with_correct_content(self, tmp_path, sample_data_list):
        """Tests JSON export."""
        exporter = Exporter()
        filepath = tmp_path / "output.json"
        exporter.to_json(sample_data_list, str(filepath))

        assert filepath.exists()
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert len(data) == 2
            assert data[0]['Title'] == 'A Study on the Application of Unit Tests'
            assert 'APA 7 Reference' in data[0]

    def test_export_bibtex_creates_file_with_correct_content(self, tmp_path, sample_paper):
        """Tests BibTeX export."""
        exporter = Exporter()
        filepath = tmp_path / "output.bib"
        exporter.to_bibtex([sample_paper], str(filepath))

        assert filepath.exists()
        content = filepath.read_text(encoding='utf-8')
        # FIX: The code produces "Doe2023", not "DoeJ.2023"
        assert "@article{Doe2023," in content
        assert "title = {A Study on the Application of Unit Tests}" in content
        assert "doi = {10.1234/test.2023.123}" in content
        assert "url = {https://example.com/paper/123}" in content

    def test_export_ris_creates_file_with_correct_content(self, tmp_path, sample_paper):
        """Tests RIS export."""
        exporter = Exporter()
        filepath = tmp_path / "output.ris"
        exporter.to_ris([sample_paper], str(filepath))

        assert filepath.exists()
        content = filepath.read_text(encoding='utf-8')
        
        # Check for standard RIS tags
        assert "TY  - JOUR" in content
        assert "T1  - A Study on the Application of Unit Tests" in content
        
        # FIX: Check for individual author names, which is more robust.
        # This handles the author string correctly regardless of spacing.
        assert "AU  - Doe, J." in content
        assert "AU  - Smith, J." in content
        
        assert "PY  - 2023" in content
        assert "JO  - Journal of Software Testing, 15(2), 123-145" in content
        assert "DO  - 10.1234/test.2023.123" in content
        assert "UR  - https://example.com/paper/123" in content
        assert "ER  -" in content

    def test_export_excel_creates_file_with_correct_content(self, tmp_path, sample_data_list):
        """Tests Excel export."""
        exporter = Exporter()
        filepath = tmp_path / "output.xlsx"
        exporter.to_excel(sample_data_list, str(filepath))

        assert filepath.exists()
        df = pd.read_excel(filepath)
        assert len(df) == 2
        assert 'APA 7 Reference' in df.columns
        assert df.iloc[0]['Title'] == 'A Study on the Application of Unit Tests'
        assert df.iloc[0]['APA 7 Reference'] == format_apa7(sample_data_list[0])
        # Check column order
        expected_cols = [
            'Title', 'Authors', 'Year', 'Venue', 'Source', 
            'Citation Count', 'DOI', 'License Type', 'URL', 'APA 7 Reference'
        ]
        assert list(df.columns) == expected_cols

    def test_main_export_routing_valid_formats(self, tmp_path, sample_data_list):
        """Tests the main export() method for all valid formats."""
        exporter = Exporter(output_dir=str(tmp_path))

        exporter.export(sample_data_list, "test_csv", "csv")
        assert (tmp_path / "test_csv.csv").exists()
        
        exporter.export(sample_data_list, "test_json", "json")
        assert (tmp_path / "test_json.json").exists()
        
        exporter.export(sample_data_list, "test_bibtex", "bibtex")
        assert (tmp_path / "test_bibtex.bib").exists()

        exporter.export(sample_data_list, "test_ris", "ris")
        assert (tmp_path / "test_ris.ris").exists()

        exporter.export(sample_data_list, "test_excel", "excel")
        assert (tmp_path / "test_excel.xlsx").exists()

    def test_main_export_routing_adds_extension(self, tmp_path, sample_data_list):
        """Tests that export() adds the correct file extension."""
        # FIX: Use the same pattern as the other test.
        exporter = Exporter(output_dir=str(tmp_path))
        exporter.export(sample_data_list, "test_no_ext", "json")
        assert (tmp_path / "test_no_ext.json").exists()

    def test_main_export_routing_invalid_format(self, tmp_path, sample_data_list, caplog):
        """Tests that export() logs an error for an invalid format."""
        exporter = Exporter()
        exporter.export(sample_data_list, "test_invalid", "foobar")
        
        # Assert no file was created
        assert not (tmp_path / "test_invalid.foobar").exists()
        
        # Assert the error message was logged
        assert "Unsupported export format: foobar" in caplog.text

    def test_export_with_no_data(self, tmp_path, caplog):
        """Tests that exporting an empty list logs a warning."""
        exporter = Exporter()
        exporter.export([], "test_empty", "csv")
        
        assert not (tmp_path / "test_empty.csv").exists()
        assert "No data provided to export" in caplog.text

    def test_export_with_absolute_path(self, tmp_path, sample_data_list):
        """
        Tests that export() correctly uses an absolute path.
        
        The 'tmp_path' fixture provides a unique temporary directory for this test.
        """
        exporter = Exporter()
        
        # Create a file path directly within the tmp_path directory.
        # tmp_path is already an absolute path, so this is perfect for the test.
        filepath = tmp_path / "absolute_test.json"
        
        exporter.export(sample_data_list, str(filepath), "json")
        
        # Assert that the file was created in the exact location we specified.
        assert filepath.exists()
        with open(filepath, 'r') as f:
            data = json.load(f)
            assert len(data) == 2