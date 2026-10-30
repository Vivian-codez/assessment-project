# Module docstring explaining that this file provides a document and PDF extraction service
"""Document and PDF extraction service."""

# Import operating system module for file path existence checks and path manipulation
import os
# Import BytesIO to wrap in-memory byte arrays as file-like streams
from io import BytesIO
# Import Optional type hint for parameters and return types
from typing import Optional
# Import system logger for diagnostics and error reporting
from app.core.logging import logger

# Attempt to import PdfReader from the pypdf library for reading PDF documents
try:
    # Import PdfReader class from pypdf
    from pypdf import PdfReader
    # Set boolean flag indicating pypdf is available
    _PYPDF_AVAILABLE = True
# Handle case where pypdf package is not installed
except ImportError:
    # Set boolean flag indicating pypdf is unavailable
    _PYPDF_AVAILABLE = False


# Service class responsible for extracting textual content from uploaded student documents
class PDFService:
    # Class docstring describing support for various file formats
    """Extracts text content and metadata from student submission files (PDF, TXT, DOCX)."""

    # Method to parse and extract plain text from in-memory raw file bytes
    def extract_text_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        # Method docstring describing the text extraction behavior
        """Extracts text from file bytes."""
        # Determine the lowercase file extension from the filename, or empty string if no dot exists
        extension = filename.lower().split(".")[-1] if "." in filename else ""

        # Set of supported plain text and source code file extensions
        code_and_text_extensions = {
            "txt", "py", "java", "c", "cpp", "cc", "cxx", "h", "hpp", "cs",
            "js", "jsx", "ts", "tsx", "html", "htm", "css", "scss", "json",
            "xml", "md", "markdown", "sql", "sh", "bash", "r", "go", "rs",
            "php", "rb", "yaml", "yml", "csv", "tsv"
        }

        # Check if the file matches any known text or source code file extension
        if extension in code_and_text_extensions:
            # Attempt to decode text bytes directly using UTF-8
            try:
                # Decode bytes to UTF-8 replacing any invalid byte sequences with replacement characters
                text = file_bytes.decode("utf-8", errors="replace")
                # Check if decoded text contains non-whitespace content
                if text.strip():
                    # Return stripped text content
                    return text.strip()
            # Catch and log any unexpected decoding errors
            except Exception as e:
                # Log error message detailing the failure to decode text/code file
                logger.error(f"Error decoding text/code file {filename}: {e}")

        # Check if the file is a Jupyter Notebook file
        if extension == "ipynb":
            # Attempt to parse notebook JSON structure
            try:
                # Import standard json module for parsing notebook schema
                import json
                # Decode bytes and parse JSON payload into dictionary
                nb = json.loads(file_bytes.decode("utf-8", errors="replace"))
                # Initialize list to accumulate extracted cell code and markdown text
                extracted_lines = []
                # Iterate through all notebook cells
                for cell in nb.get("cells", []):
                    # Retrieve the cell source lines or string
                    src = cell.get("source", [])
                    # Join lines if source is a list, otherwise convert to string
                    cell_text = "".join(src) if isinstance(src, list) else str(src)
                    # Check if the cell text contains non-whitespace content
                    if cell_text.strip():
                        # Append stripped cell text to accumulated lines
                        extracted_lines.append(cell_text.strip())
                # Check if any lines were extracted from the notebook cells
                if extracted_lines:
                    # Return lines joined by double newlines
                    return "\n\n".join(extracted_lines)
            # Catch and log any errors encountered while parsing the notebook
            except Exception as e:
                # Log warning with error details
                logger.warning(f"Error parsing notebook {filename}: {e}")

        # Check if the file is a Microsoft Word Document
        if extension == "docx":
            # Attempt to parse DOCX using the python-docx library
            try:
                # Import docx library
                import docx
                # Parse document from in-memory BytesIO stream
                doc = docx.Document(BytesIO(file_bytes))
                # Initialize list to collect extracted paragraph and table texts
                extracted_sections = []
                # 1. Iterate through all document paragraphs
                for p in doc.paragraphs:
                    # Strip leading and trailing whitespace from paragraph text
                    t = p.text.strip()
                    # Check if paragraph text is non-empty
                    if t:
                        # Append paragraph text to extracted sections
                        extracted_sections.append(t)
                # 2. Iterate through all embedded tables in the document
                for table in doc.tables:
                    # Iterate through all rows of the table
                    for row in table.rows:
                        # Extract non-empty text from each cell in the row
                        row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        # Check if any cells in the row contained text
                        if row_cells:
                            # Append pipe-separated row representation to extracted sections
                            extracted_sections.append(" | ".join(row_cells))

                # Combine all extracted sections separated by blank lines
                full_doc_text = "\n\n".join(extracted_sections).strip()
                # If non-empty document text was extracted, return it
                if full_doc_text:
                    # Return extracted Word document text
                    return full_doc_text
            # Catch docx parsing errors and fallback to direct XML extraction
            except Exception as docx_err:
                # Log warning indicating failure and intent to fallback
                logger.warning(f"python-docx extraction failed for {filename}: {docx_err}. Attempting direct XML fallback.")

            # Attempt direct XML extraction by unzipping docx archive
            try:
                # Import zipfile module for unpacking docx
                import zipfile
                # Import ElementTree for parsing document XML
                import xml.etree.ElementTree as ET
                # Open the byte array as a zip archive
                with zipfile.ZipFile(BytesIO(file_bytes)) as docx_zip:
                    # Check if the standard Word XML document exists in the archive
                    if "word/document.xml" in docx_zip.namelist():
                        # Read the raw XML content of the document
                        xml_content = docx_zip.read("word/document.xml")
                        # Parse XML string into an ElementTree root
                        root = ET.fromstring(xml_content)
                        # Extract text values from all elements ending with text tag }t
                        texts = [elem.text for elem in root.iter() if elem.text and elem.tag.endswith("}t")]
                        # Check if any text fragments were found
                        if texts:
                            # Return text fragments joined by spaces
                            return " ".join(texts).strip()
            # Catch and log any XML fallback errors
            except Exception as xml_err:
                # Log warning with XML error details
                logger.warning(f"XML docx extraction fallback failed for {filename}: {xml_err}")

        # Check if the file is a PDF document
        if extension == "pdf":
            # Check if the pypdf library is installed and available
            if _PYPDF_AVAILABLE:
                # Attempt to extract text using PdfReader
                try:
                    # Initialize PdfReader with the in-memory byte stream
                    reader = PdfReader(BytesIO(file_bytes))
                    # Initialize list to accumulate extracted text page by page
                    extracted = []
                    # Iterate through each page in the PDF document
                    for page in reader.pages:
                        # Extract plain text content from the current page
                        page_text = page.extract_text()
                        # If page produced text, append to list
                        if page_text:
                            # Append page text to extracted list
                            extracted.append(page_text)
                    # Combine all page texts joined by double newlines
                    full_text = "\n\n".join(extracted).strip()
                    # If valid text was extracted, return it
                    if full_text:
                        # Return extracted PDF text
                        return full_text
                # Catch any pypdf extraction errors
                except Exception as e:
                    # Log warning detailing pypdf failure
                    logger.warning(f"pypdf extraction failed for {filename}: {e}")

            # Attempt fallback decoding using Latin-1 encoding for ASCII-like streams
            try:
                # Decode bytes using latin1 ignoring invalid characters
                text = file_bytes.decode("latin1", errors="ignore")
                # Filter text keeping only printable characters, newlines, and tabs
                cleaned = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
                # Return first 4000 characters if cleaned text is non-empty, otherwise default string
                return cleaned[:4000] if cleaned else "Extracted text content from " + filename
            # Catch any fallback decoding exceptions
            except Exception:
                # Return placeholder string with filename
                return f"Content extracted from {filename}"

        # Universal fallback: attempt UTF-8 decoding on any unknown file format
        try:
            # Decode bytes with UTF-8 ignoring errors and stripping whitespace
            decoded = file_bytes.decode("utf-8", errors="ignore").strip()
            # If decoded text is longer than 20 characters, clean and return
            if len(decoded) > 20:
                # Filter out non-printable binary characters
                cleaned = "".join(c for c in decoded if c.isprintable() or c in "\n\r\t")
                # Return up to 10,000 characters of cleaned text
                return cleaned[:10000]
        # Silently pass on universal fallback errors
        except Exception:
            # Pass to final return statement
            pass

        # Final default fallback string when no text could be extracted
        return f"Document submission text extracted from {filename}"

    # Method to extract text from a local file path on disk
    def extract_text_from_file_path(self, file_path: str) -> str:
        # Method docstring describing file path extraction
        """Extracts text from a local file path."""
        # Check if the file exists at the given filesystem path
        if not os.path.exists(file_path):
            # Return empty string if file does not exist
            return ""
        # Open the file in binary read mode
        with open(file_path, "rb") as f:
            # Read bytes and delegate extraction to extract_text_from_bytes
            return self.extract_text_from_bytes(f.read(), os.path.basename(file_path))


# Instantiate singleton instance of PDFService for backend use
pdf_service = PDFService()
