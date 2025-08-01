import unittest
from ai.services.iso_pecb_parser import extract_and_verify_pecb, extract_pecb_fields, is_valid_pecb_certificate
import os

class PECBParserTest(unittest.TestCase):
    def setUp(self):
        self.test_files = {
            'pecb_valid': "ai/datasets/ISO/PECB/pecb_3.jpeg",  # Update path as needed
        }

        for name, path in self.test_files.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Test file not found: {path}")

    def test_extract_and_verify(self):
        """Test field extraction and live verification"""
        for name, path in self.test_files.items():
            result = extract_and_verify_pecb(path)
            print(f"\n[TEST: {name}] Parsed Result:\n{result}")

            self.assertIn("recipient_name", result)
            self.assertIn("certificate_title", result)
            self.assertIn("certificate_number", result)
            self.assertIn("verification_status", result)
            self.assertIn(result["verification_status"], ["verified", "verification_failed", "invalid_document_format"])

            if result["verification_status"] == "verified":
                verification = result["verification_details"]
                self.assertIn("first_name", verification)
                self.assertIn("certificate_title", verification)
                self.assertIn("status", verification)
                print(f"✅ Verification Passed: {verification['status']}")
            elif result["verification_status"] == "verification_failed":
                print(f"⚠️ Verification Failed Reason: {result.get('verification_details')}")

    def test_structure_check(self):
        """Ensure valid PECB certificate format is detected from text"""
        dummy_text = '''
        PECB
        Professional Evaluation and Certification Board
        hereby attests that Jane Smith
        Certificate Holder in ISO/IEC 27001:2022 Foundation
        Certificate Number: ISLA1234567-2023-01
        Issue Date: 2023-01-10
        Carolina Cabezas
        '''
        self.assertTrue(is_valid_pecb_certificate(dummy_text))

if __name__ == "__main__":
    unittest.main()
