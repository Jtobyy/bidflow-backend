import pytesseract
from PIL import Image

def extract_text_from_image(image_path):
    """
    Extracts text from a given image file using OCR.
    For now, returns dummy text if Tesseract is not set up.
    """
    try:
        text = pytesseract.image_to_string(Image.open(image_path))
        return text
    except Exception as e:
        print(e)
        return "Dummy extracted text for testing."
