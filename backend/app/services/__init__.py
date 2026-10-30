# Module docstring explaining that this package aggregates application domain services
"""Services package."""

# Import the singleton instance of GeminiService for LLM evaluations and plagiarism detection
from app.services.gemini_service import gemini_service
# Import the singleton instance of VectorService for Qdrant vector embeddings and similarity checks
from app.services.vector_service import vector_service
# Import the singleton instance of SupabaseService for database data operations
from app.services.supabase_service import supabase_service
# Import the singleton instance of PDFService for extracting text and metadata from PDF files
from app.services.pdf_service import pdf_service
# Import the singleton instance of FerpaService for PII encryption and decryption
from app.services.ferpa_service import ferpa_service

# Define explicit public exports for the services package
__all__ = [
    # Export Gemini AI service instance
    "gemini_service",
    # Export vector embedding service instance
    "vector_service",
    # Export database query service instance
    "supabase_service",
    # Export PDF extraction service instance
    "pdf_service",
    # Export FERPA compliance encryption service instance
    "ferpa_service",
]
