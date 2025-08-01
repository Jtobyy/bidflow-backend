import unittest
import os
from ai.services.bid_parser import parse_bid_document
from ai.services.pdf_text import extract_text_from_pdf

class BidParserTest(unittest.TestCase):
    def setUp(self):
        self.test_files = {
            'valid_bid': "ai/datasets/BID/sample_bid_1.pdf",
            'empty_bid': "ai/datasets/BID/empty_bid.pdf"
        }

        for name, path in self.test_files.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Test file not found: {path}")

        self.tender_title = "Supply of Educational Tablets"
        self.tender_description = (
            "The procurement seeks qualified vendors to supply durable Android-based tablets with at least 8-inch screens, "
            "2GB RAM, and 32GB storage, including accessories and warranty."
        )

    def test_extract_text_from_pdf(self):
        """Ensure text is extracted from a valid bid PDF"""
        text = extract_text_from_pdf(self.test_files['valid_bid'])
        print(f"\nExtracted Bid Text (First 500 chars):\n{text[:500]}")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 100)

    def test_parse_valid_bid(self):
        """Test AI scoring on a valid bid PDF"""
        result = parse_bid_document(
            self.test_files['valid_bid'],
            self.tender_title,
            self.tender_description
        )

        print(f"\nBid Evaluation Result:\n{result}")

        self.assertIn("score", result)
        self.assertIn("status", result)
        self.assertIn(result["status"], ["analyzed", "incomplete_analysis", "error"])
        self.assertIsInstance(result["score"], int)

        if result["status"] == "analyzed":
            self.assertIn("evaluation", result)
            self.assertIn("strengths", result["evaluation"])
            self.assertIn("weaknesses", result["evaluation"])
            self.assertIn("comment", result["evaluation"])

    def test_parse_empty_bid(self):
        """Test behavior with an empty or blank bid document"""
        result = parse_bid_document(
            self.test_files['empty_bid'],
            self.tender_title,
            self.tender_description
        )

        print(f"\nEmpty Bid Result:\n{result}")

        self.assertEqual(result["status"], "empty_document")
        self.assertEqual(result["score"], 0)

if __name__ == "__main__":
    unittest.main()
