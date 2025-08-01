# ai/utils/pdf_text.py
import pdfplumber

def extract_text_from_pdf(path: str) -> str:
    """
    Extract text from a PDF using pdfplumber (non-OCR).

    Args:
        path (str): Path to the PDF file.

    Returns:
        str: Extracted plain text from all pages.
    """
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()
