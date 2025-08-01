# ai/utils/vision_ocr.py
import os
from google.cloud import vision

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'bidflow-466722-ef0519222bd5.json'

def detect_text_from_image(image_path: str) -> str:
    """
    Extract visible text from an image using Google Cloud Vision API.
    
    Args:
        image_path (str): Path to the image file.

    Returns:
        str: Detected text content or "No text detected".
    """
    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    if not response.text_annotations:
        return "No text detected"
    
    if response.error.message:
        raise Exception(
            f"{response.error.message}\nMore info: https://cloud.google.com/apis/design/errors"
        )
    
    return response.text_annotations[0].description
