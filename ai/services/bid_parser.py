# ai/services/bid_parser.py

from .pdf_text import extract_text_from_pdf
import requests
import re
import json

def query_ollama_for_bid_analysis(tender_text: str, bid_text: str) -> dict:
    """
    Sends tender and bid text to Ollama for analysis.
    """
    prompt = f"""
You are a procurement evaluation assistant. You help score bid submissions against tender requirements.

Here is a tender (full text):
---
{tender_text[:4000]}
---

Here is a bid submission:
---
{bid_text[:4000]}
---

Based on this, Return ONLY a valid JSON object like this:
{{
  "relevance_score": 82,
  "strengths": ["Clear methodology", "Local experience"],
  "weaknesses": ["No financials"],
  "evaluator_comment": "The bid meets most requirements but lacks cost clarity."
}}
"""

    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }, timeout=360)

        # print('response is ', response)
        if response.status_code == 200:
            # print('response is ', response.text)
            response_text = response.json().get("response", "")

            # Try to extract JSON block from markdown or free-text response
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                return {
                    "status": "ollama_error",
                    "error": "AI response did not include valid JSON block.",
                    "raw_text": response_text
                }
        else:
            return {
                "status": "ollama_error",
                "error": f"Failed to get response from Ollama: {response.status_code} - {response.text}"
            }

    except Exception as e:
        return {
            "status": "ollama_exception",
            "error": str(e)
        }


def parse_bid_document(bid_file_path: str, tender_title: str, tender_description: str) -> dict:
    """
    Uses AI to evaluate a bid document against the tender.

    Returns a structured report including relevance, strengths, weaknesses, and a score.
    """
    try:
        bid_text = extract_text_from_pdf(bid_file_path)

        if not bid_text.strip():
            return {
                "score": 0,
                "status": "empty_document",
                "reason": "No extractable text found in the PDF.",
                "evaluation": {}
            }

        analysis = query_ollama_for_bid_analysis(tender_title, tender_description, bid_text)

        if "relevance_score" in analysis:
            return {
                "score": analysis["relevance_score"],
                "status": "analyzed",
                "evaluation": {
                    "strengths": analysis.get("strengths", []),
                    "weaknesses": analysis.get("weaknesses", []),
                    "comment": analysis.get("evaluator_comment", "")
                }
            }
        else:
            return {
                "score": 0,
                "status": "incomplete_analysis",
                "reason": "AI did not return expected structure.",
                "raw_response": analysis
            }

    except Exception as e:
        return {
            "score": 0,
            "status": "error",
            "reason": str(e),
            "evaluation": {}
        }

def parse_bid_document(bid_file_path: str, tender: 'Tender') -> dict:
    """
    Uses AI to evaluate a bid document against the tender, using the full tender document if available.

    Returns a structured report including relevance, strengths, weaknesses, and a score.
    """
    try:
        bid_text = extract_text_from_pdf(bid_file_path)

        if not bid_text.strip():
            return {
                "score": 0,
                "status": "empty_document",
                "reason": "No extractable text found in the bid PDF.",
                "evaluation": {}
            }

        if tender.tender_document:
            tender_text = extract_text_from_pdf(tender.tender_document.path)
        else:
            tender_text = f"Title: {tender.title}\nDescription: {tender.description}"

        analysis = query_ollama_for_bid_analysis(tender_text, bid_text)

        if "relevance_score" in analysis:
            return {
                "score": analysis["relevance_score"],
                "status": "analyzed",
                "evaluation": {
                    "strengths": analysis.get("strengths", []),
                    "weaknesses": analysis.get("weaknesses", []),
                    "comment": analysis.get("evaluator_comment", "")
                }
            }
        else:
            return {
                "score": 0,
                "status": "incomplete_analysis",
                "reason": "AI did not return expected structure.",
                "raw_response": analysis
            }

    except Exception as e:
        return {
            "score": 0,
            "status": "error",
            "reason": str(e),
            "evaluation": {}
        }
