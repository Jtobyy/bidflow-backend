import unittest
from ai.services.cac_parser import extract_cac_fields, extract_registration_number, extract_company_name
import os

class CACParserTest(unittest.TestCase):
    def setUp(self):
        # Setup test file paths
        self.test_files = {
            'rc_sample': "ai/datasets/nigeria/CAC/cac_6.JPG",
            'bn_sample': "ai/datasets/nigeria/CAC/cac_7.JPG",
            # 'trustee_sample': "ai/datasets/nigeria/CAC/trustee_sample.jpg"
        }
        
        # Verify test files exist
        for name, path in self.test_files.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Test file not found: {path}")

    def test_extract_fields_full_rc(self):
        """Test full field extraction for RC sample"""
        result = extract_cac_fields(self.test_files['rc_sample'])

        # Debug output
        print(f"\nParsed Fields (RC): {result}")

        # Assertions
        self.assertIn("company_name", result)
        self.assertIsNotNone(result["company_name"], "Company name was not found")
        self.assertIsInstance(result["company_name"], str)

        self.assertIn("registration_number", result)
        self.assertIsNotNone(result["registration_number"], "Registration number was not found")
        self.assertTrue(result["registration_number"].isdigit(), 
                       f"Registration number invalid: {result['registration_number']}")
        
        self.assertIn("registration_type", result)
        self.assertEqual(result["registration_type"], "RC")
        
        self.assertIn("full_registration_number", result)
        self.assertTrue(result["full_registration_number"].startswith("RC"))
        
        self.assertIn("verification_status", result)

    def test_extract_fields_full_bn(self):
        """Test full field extraction for Business Name sample"""
        result = extract_cac_fields(self.test_files['bn_sample'])

        # Debug output
        print(f"\nParsed Fields (BN): {result}")

        # Assertions
        self.assertIn("company_name", result)
        self.assertIsNotNone(result["company_name"], "Company name was not found")

        self.assertIn("registration_number", result)
        self.assertIsNotNone(result["registration_number"], "Registration number was not found")
        
        self.assertIn("registration_type", result)
        self.assertEqual(result["registration_type"], "BN")
        
        self.assertIn("full_registration_number", result)
        self.assertTrue(result["full_registration_number"].startswith("BN"))

    def test_extract_registration_number(self):
        """Test registration number extraction from sample text"""
        # RC number test
        rc_text = "COMPANY REGISTRATION NO. 1924691"
        rc_result = extract_registration_number(rc_text)
        self.assertEqual(rc_result["type"], "RC")
        self.assertEqual(rc_result["number"], "1924691")
        self.assertEqual(rc_result["full_number"], "RC1924691")

        # BN number test
        bn_text = "Registered as a business name with number 123456"
        bn_result = extract_registration_number(bn_text)
        self.assertEqual(bn_result["type"], "BN")
        self.assertEqual(bn_result["number"], "123456")
        self.assertEqual(bn_result["full_number"], "BN123456")

    def test_extract_company_name(self):
        """Test company name extraction from sample text"""
        # Regular company
        company_text = "This is to certify that ACME CORPORATIONS LIMITED is duly registered"
        company_name = extract_company_name(company_text)
        print(f'company name {company_name}')
        self.assertEqual(company_name, "ACME CORPORATIONS LIMITED")

        # Trustee organization
        trustee_text = "The Incorporated Trustees of GREEN EARTH FOUNDATION"
        trustee_name = extract_company_name(trustee_text)
        self.assertEqual(trustee_name, "GREEN EARTH FOUNDATION")

    def test_error_handling(self):
        """Test error handling with invalid input"""
        # Test with non-existent file
        result = extract_cac_fields("non_existent_file.jpg")
        self.assertIn("error", result)
        
        # Test with empty text
        empty_result = extract_registration_number("")
        self.assertIsNone(empty_result["number"])
        self.assertIsNone(empty_result["type"])

if __name__ == "__main__":
    unittest.main()