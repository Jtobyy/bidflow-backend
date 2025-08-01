import unittest
import os
from ai.services.tin_parser import (
    extract_and_verify_tin,
    extract_tin_fields,
    is_valid_tin_certificate
)

class TINParserTest(unittest.TestCase):
    def setUp(self):
        # Set up test file paths
        self.test_files = {
            'valid_tin': "ai/datasets/nigeria/TIN/tin_4.jpg",
            'invalid_format': "ai/datasets/nigeria/TIN/invalid_tin_1.png"
        }

        # Verify test files exist
        for name, path in self.test_files.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Test file not found: {path}")

    def test_extract_and_verify_valid_tin(self):
        """Test full extraction and verification from a valid TIN certificate"""
        result = extract_and_verify_tin(self.test_files['valid_tin'])

        print(f"\nParsed TIN Result: {result}")

        self.assertIn("tin_number", result)
        self.assertIsInstance(result["tin_number"], str)

        self.assertIn("taxpayer_name", result)
        self.assertIsInstance(result["taxpayer_name"], str)

        self.assertIn("verification_status", result)
        self.assertIn(result["verification_status"], ["verified", "verification_failed", "verification_unavailable"])

    def test_extract_fields(self):
        """Test field extraction from raw text"""
        with open(self.test_files['valid_tin'], 'rb') as f:
            from ai.services.vision_ocr import detect_text_from_image
            text = detect_text_from_image(self.test_files['valid_tin'])

        fields = extract_tin_fields(text)

        self.assertIn("tin_number", fields)
        self.assertIsInstance(fields["tin_number"], (str, type(None)))

        self.assertIn("taxpayer_name", fields)
        self.assertIsInstance(fields["taxpayer_name"], (str, type(None)))

        self.assertIn("is_valid_format", fields)
        self.assertIsInstance(fields["is_valid_format"], bool)

    def test_invalid_tin_document_format(self):
        """Check that invalid documents are correctly flagged"""
        with open(self.test_files['invalid_format'], 'rb') as f:
            from ai.services.vision_ocr import detect_text_from_image
            text = detect_text_from_image(self.test_files['invalid_format'])

        valid = is_valid_tin_certificate(text)
        print(f'validity {valid}')
        self.assertFalse(valid)

    def test_error_handling_non_existent_file(self):
        """Ensure graceful failure when image path is incorrect"""
        result = extract_and_verify_tin("ai/datasets/nigeria/TIN/not_a_file.jpg")
        self.assertIn("error", result)
        self.assertEqual(result["verification_status"], "processing_error")

if __name__ == "__main__":
    unittest.main()