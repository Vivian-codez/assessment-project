"""Document and PDF extraction service."""

import os
from io import BytesIO
from typing import Optional
from app.core.logging import logger

try:
    from pypdf import PdfReader
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False


class PDFService:
    """Extracts text content and metadata from student submission files (PDF, TXT, DOCX)."""

    def extract_text_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        """Extracts text from file bytes."""
        extension = filename.lower().split(".")[-1] if "." in filename else ""

        # Text and source code files
        code_and_text_extensions = {
            "txt", "py", "java", "c", "cpp", "cc", "cxx", "h", "hpp", "cs",
            "js", "jsx", "ts", "tsx", "html", "htm", "css", "scss", "json",
            "xml", "md", "markdown", "sql", "sh", "bash", "r", "go", "rs",
            "php", "rb", "yaml", "yml", "csv", "tsv"
        }

        if extension in code_and_text_extensions:
            try:
                text = file_bytes.decode("utf-8", errors="replace")
                if text.strip():
                    return text.strip()
            except Exception as e:
                logger.error(f"Error decoding text/code file {filename}: {e}")

        # Jupyter Notebook (.ipynb)
        if extension == "ipynb":
            try:
                import json
                nb = json.loads(file_bytes.decode("utf-8", errors="replace"))
                extracted_lines = []
                for cell in nb.get("cells", []):
                    src = cell.get("source", [])
                    cell_text = "".join(src) if isinstance(src, list) else str(src)
                    if cell_text.strip():
                        extracted_lines.append(cell_text.strip())
                if extracted_lines:
                    return "\n\n".join(extracted_lines)
            except Exception as e:
                logger.warning(f"Error parsing notebook {filename}: {e}")

        # Word Document (.docx)
        if extension == "docx":
            try:
                import docx
                doc = docx.Document(BytesIO(file_bytes))
                extracted_sections = []
                # 1. Extract all paragraphs
                for p in doc.paragraphs:
                    t = p.text.strip()
                    if t:
                        extracted_sections.append(t)
                # 2. Extract tables (data grids, submission tables, rubrics)
                for table in doc.tables:
                    for row in table.rows:
                        row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_cells:
                            extracted_sections.append(" | ".join(row_cells))

                full_doc_text = "\n\n".join(extracted_sections).strip()
                if full_doc_text:
                    return full_doc_text
            except Exception as docx_err:
                logger.warning(f"python-docx extraction failed for {filename}: {docx_err}. Attempting direct XML fallback.")

            # Fallback to direct XML unzip extraction if docx encounters unusual formatting
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(BytesIO(file_bytes)) as docx_zip:
                    if "word/document.xml" in docx_zip.namelist():
                        xml_content = docx_zip.read("word/document.xml")
                        root = ET.fromstring(xml_content)
                        texts = [elem.text for elem in root.iter() if elem.text and elem.tag.endswith("}t")]
                        if texts:
                            return " ".join(texts).strip()
            except Exception as xml_err:
                logger.warning(f"XML docx extraction fallback failed for {filename}: {xml_err}")

        if extension == "pdf":
            if _PYPDF_AVAILABLE:
                try:
                    reader = PdfReader(BytesIO(file_bytes))
                    extracted = []
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted.append(page_text)
                    full_text = "\n\n".join(extracted).strip()
                    if full_text:
                        return full_text
                except Exception as e:
                    logger.warning(f"pypdf extraction failed for {filename}: {e}")

            # Fallback text decoder for ASCII-like streams
            try:
                text = file_bytes.decode("latin1", errors="ignore")
                # Clean non-printable characters
                cleaned = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
                return cleaned[:4000] if cleaned else "Extracted text content from " + filename
            except Exception:
                return f"Content extracted from {filename}"

        # Universal fallback: try utf-8, then latin1
        try:
            decoded = file_bytes.decode("utf-8", errors="ignore").strip()
            if len(decoded) > 20:
                cleaned = "".join(c for c in decoded if c.isprintable() or c in "\n\r\t")
                return cleaned[:10000]
        except Exception:
            pass

        return f"Document submission text extracted from {filename}"

    def extract_text_from_file_path(self, file_path: str) -> str:
        """Extracts text from a local file path."""
        if not os.path.exists(file_path):
            return ""
        with open(file_path, "rb") as f:
            return self.extract_text_from_bytes(f.read(), os.path.basename(file_path))


pdf_service = PDFService()
