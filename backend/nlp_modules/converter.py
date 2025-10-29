"""
Document converter module to convert DOCX and PPTX files to PDF
Simple approach: Just mark conversion as failed so frontend shows download option
"""
import os

def convert_to_pdf(input_path: str, output_path: str) -> bool:
    """
    Conversion placeholder - returns False to indicate no conversion available
    
    Args:
        input_path: Path to input file (DOCX or PPTX)
        output_path: Path where PDF should be saved
    
    Returns:
        bool: Always False (no conversion available without external tools)
    """
    # Conversion requires external dependencies (LibreOffice, MS Office, etc.)
    # Return False to let frontend handle display appropriately
    return False
