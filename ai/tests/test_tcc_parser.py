import unittest
import os
from ai.services.tcc_parser import (
    extract_and_verify_tcc,
    extract_tcc_fields,
    is_valid_tcc_certificate
)

class TCCParserTest(unittest.TestCase):
    def setUp(self):
        # Set up test file paths
        self.test_files = {
            'valid_tcc': "ai/datasets/nigeria/TCC/tcc_4.JPG",  # This one is expired (2022-12-31)
            'valid_non_expired_tcc': "ai/datasets/nigeria/TCC/tcc_5.JPG",  # You'll need a non-expired one
            'invalid_format': "ai/datasets/nigeria/TCC/invalid_tcc_1.jpg"
        }

        # Only check for files that should exist for each test
        required_files = ['valid_tcc', 'invalid_format']  # Don't require non-expired one yet
        for name in required_files:
            path = self.test_files[name]
            if not os.path.exists(path):
                raise FileNotFoundError(f"Test file not found: {path}")

    def test_extract_and_verify_valid_non_expired_tcc(self):
        """Test full extraction and verification from a valid, non-expired TCC certificate"""
        # Skip this test if we don't have a non-expired certificate yet
        if not os.path.exists(self.test_files['valid_non_expired_tcc']):
            self.skipTest("No non-expired TCC certificate available for testing")
            
        result = extract_and_verify_tcc(self.test_files['valid_non_expired_tcc'])

        print(f"\nParsed Valid TCC Result: {result}")

        # Should have basic fields extracted
        self.assertIn("tin_number", result)
        self.assertIsInstance(result["tin_number"], str)

        self.assertIn("taxpayer_name", result)
        self.assertIsInstance(result["taxpayer_name"], str)

        self.assertIn("verification_status", result)
        
        # Should be verified or verification_failed (not expired)
        self.assertIn(result["verification_status"], ["verified", "verification_failed", "verification_unavailable"])
        
        # Should have verification_details (since it's not expired)
        self.assertIn("verification_details", result)
        
        print("✓ Valid non-expired certificate processed correctly")

    def test_extract_and_verify_expired_tcc(self):
        """Test that expired TCC certificates are correctly identified"""
        result = extract_and_verify_tcc(self.test_files['valid_tcc'])  # This one expires 2022-12-31

        print(f"\nParsed Expired TCC Result: {result}")

        # Should have basic fields extracted
        self.assertIn("tin_number", result)
        self.assertIsInstance(result["tin_number"], str)

        self.assertIn("taxpayer_name", result)
        self.assertIsInstance(result["taxpayer_name"], str)

        # Should be identified as expired
        self.assertEqual(result["verification_status"], "expired_certificate")
        
        # Should have expiration date and error message
        self.assertIn("expiration_date", result)
        self.assertIsInstance(result["expiration_date"], str)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Certificate has expired")
        
        # Should NOT have verification_details (since we don't verify expired certs)
        self.assertNotIn("verification_details", result)
        
        print("✓ Expired certificate correctly identified and rejected")

    def test_extract_fields_from_valid_tcc(self):
        """Test field extraction from raw text"""
        from ai.services.vision_ocr import detect_text_from_image
        text = detect_text_from_image(self.test_files['valid_tcc'])

        fields = extract_tcc_fields(text)

        # Check all expected fields are present
        self.assertIn("tin_number", fields)
        self.assertIsInstance(fields["tin_number"], (str, type(None)))

        self.assertIn("taxpayer_name", fields)
        self.assertIsInstance(fields["taxpayer_name"], (str, type(None)))

        self.assertIn("rc_number", fields)
        self.assertIsInstance(fields["rc_number"], (str, type(None)))

        self.assertIn("expiration_date", fields)
        self.assertIsInstance(fields["expiration_date"], (str, type(None)))

        self.assertIn("is_valid_format", fields)
        self.assertIsInstance(fields["is_valid_format"], bool)

        # For our test file, we know these should be extracted
        self.assertIsNotNone(fields["tin_number"])
        self.assertIsNotNone(fields["taxpayer_name"])
        self.assertIsNotNone(fields["rc_number"])
        self.assertIsNotNone(fields["expiration_date"])
        self.assertTrue(fields["is_valid_format"])

        # Print extracted fields for debugging
        print(f"\nExtracted fields:")
        print(f"  TIN: {fields['tin_number']}")
        print(f"  Name: {fields['taxpayer_name']}")
        print(f"  RC: {fields['rc_number']}")
        print(f"  Expiration: {fields['expiration_date']}")
        print(f"  Valid format: {fields['is_valid_format']}")

    def test_invalid_tcc_document_format(self):
        """Check that invalid documents are correctly flagged"""
        from ai.services.vision_ocr import detect_text_from_image
        text = detect_text_from_image(self.test_files['invalid_format'])

        valid = is_valid_tcc_certificate(text)
        print(f'Document format validity: {valid}')
        self.assertFalse(valid)

        # Test the full extraction pipeline with invalid format
        result = extract_and_verify_tcc(self.test_files['invalid_format'])
        self.assertEqual(result["verification_status"], "invalid_document_format")
        self.assertIn("error", result)

    def test_error_handling_non_existent_file(self):
        """Ensure graceful failure when image path is incorrect"""
        result = extract_and_verify_tcc("ai/datasets/nigeria/TCC/not_a_file.jpg")
        self.assertIn("error", result)
        self.assertEqual(result["verification_status"], "processing_error")

    def test_certificate_expiration_logic(self):
        """Test that expiration date checking works correctly"""
        from ai.services.tcc_parser import is_certificate_expired
        
        # Test expired date (past)
        self.assertTrue(is_certificate_expired("2022-12-31"))
        self.assertTrue(is_certificate_expired("2020-01-01"))
        
        # Test future date (not expired)
        self.assertFalse(is_certificate_expired("2026-12-31"))
        self.assertFalse(is_certificate_expired("2030-01-01"))
        
        # Test invalid date format
        self.assertFalse(is_certificate_expired("invalid-date"))
        self.assertFalse(is_certificate_expired("31-12-2022"))  # Wrong format
        
        # Test None/empty
        self.assertFalse(is_certificate_expired(None))
        self.assertFalse(is_certificate_expired(""))
        
        print("✓ Expiration logic tests passed")

    def test_missing_tin_extraction_failure(self):
        """Test behavior when TIN cannot be extracted"""
        # You could create a mock text or image that looks like TCC but missing TIN
        # For now, we'll test the logic path
        mock_text = """
        TAX CLEARANCE CERTIFICATE
        FIRS
        Name of Company: TEST COMPANY LIMITED
        RC No: 123456
        This Certificate Expires on: 2026-12-31
        """
        
        fields = extract_tcc_fields(mock_text)
        # Should be valid format but missing TIN
        self.assertTrue(fields["is_valid_format"])
        self.assertIsNone(fields["tin_number"])

if __name__ == "__main__":
    unittest.main()