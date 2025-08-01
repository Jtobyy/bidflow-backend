# ai/services/bid_parser.py

from .pdf_text import extract_text_from_pdf
import requests

def query_ollama_for_bid_analysis(tender_title: str, tender_description: str, bid_text: str) -> dict:
    """
    Sends a prompt to Ollama to evaluate a bid in the context of a tender.

    Returns:
        dict: Structured evaluation with score, relevance, comments, etc.
    """
    prompt = f"""
You are a procurement evaluation assistant. You help score bid submissions against tender requirements.

Here is a tender:
---
Title: {tender_title}
Description: {tender_description}
---

Here is a bid submission (text extracted from the PDF):
---
{bid_text[:4000]}  # Limit input to prevent overload
---

Based on this, return a JSON object with:
- relevance_score (0 to 100)
- strengths: bullet points
- weaknesses: bullet points
- evaluator_comment: one-paragraph summary
"""

    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False
        }, timeout=60)

        if response.status_code == 200:
            result = response.json().get("response", "")
            # Attempt to parse response as JSON
            import json
            return json.loads(result)
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
