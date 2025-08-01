import os
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from google.cloud import vision
from .vision_ocr import detect_text_from_image


os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'bidflow-466722-ef0519222bd5.json'

class QoreIDClient:
    """QoreID API client for TIN verification"""
    
    def __init__(self):
        self.base_url = "https://api.qoreid.com"
        self.client_id = "N1UHQOW3PDNPK1B31X6P"
        self.secret = "17476cbb1aff42be9e835913b02b4410"
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self) -> Optional[str]:
        """Get or refresh access token"""
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at - timedelta(minutes=5)):
            return self.access_token
        
        try:
            response = requests.post(
                f"{self.base_url}/token",
                json={"clientId": self.client_id, "secret": self.secret},
                timeout=30
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                self.access_token = data.get("accessToken")
                expires_in = data.get("expiresIn", 7200)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                return self.access_token
            else:
                print(f"Failed to get QoreID token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting QoreID token: {str(e)}")
            return None
    
    def verify_tin(self, tin_number: str) -> Optional[Dict[str, Any]]:
        """Verify TIN number with QoreID API"""
        token = self.get_access_token()
        if not token:
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/v2/ng/identities/tin/{tin_number}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"TIN verification failed: {response.status_code} - {response.text}")
                return {"error": f"Verification failed: {response.status_code}"}
                
        except Exception as e:
            print(f"Error verifying TIN: {str(e)}")
            return {"error": f"Verification error: {str(e)}"}

def is_valid_tin_certificate(text: str) -> bool:
    """Validate if the document contains expected TIN certificate elements (loosely)"""
    required_keywords = [
        r'CERTIFICATE',
        r'TAXPAYER',
        r'IDENTIFICATION',
        r'NUMBER',
        r'JOINT\s+TAX\s+BOARD',
        r'Taxpayer[\'’]s Name',
        r'\bTIN\b',
        r'Date of Issue',
        r'Tax Authority',
        r'Address'
    ]
    
    matches = [re.search(pattern, text, re.IGNORECASE) for pattern in required_keywords]
    matched_count = sum(1 for m in matches if m)

    # Consider valid if 7 out of 10 keywords are matched
    return matched_count >= 7

def extract_tin_fields(text: str) -> Dict[str, str]:
    """Extract TIN number and taxpayer name from certificate text with smart proximity and 10-digit filtering"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    tin_number = None
    taxpayer_name = None

    # Step 1: Find TIN number near the word "TIN"
    for idx, line in enumerate(lines):
        if re.search(r'\bTIN\b', line, re.IGNORECASE):
            # Same line
            match = re.search(r'\bTIN\b.*?(\d{10})', line)
            if match:
                tin_number = match.group(1)
                break
            # Next line
            if idx + 1 < len(lines):
                next_match = re.search(r'\b(\d{10})\b', lines[idx + 1])
                if next_match:
                    tin_number = next_match.group(1)
                    break
            # Previous line
            if idx - 1 >= 0:
                prev_match = re.search(r'\b(\d{10})\b', lines[idx - 1])
                if prev_match:
                    tin_number = prev_match.group(1)
                    break

    # Step 2: Fallback — search all 10-digit numbers (if above fails)
    if not tin_number:
        for line in lines:
            fallback_match = re.search(r'\b(\d{10})\b', line)
            if fallback_match:
                tin_number = fallback_match.group(1)
                break

    # Step 3: Taxpayer Name extraction
    for idx, line in enumerate(lines):
        if re.search(r"Taxpayer[’']s Name", line, re.IGNORECASE):
            # Same line
            match = re.search(r"Taxpayer[’']s Name\s*[:#-]?\s*(.+)", line, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                if len(raw) > 2:
                    taxpayer_name = raw
                    break
            # Next line
            if idx + 1 < len(lines):
                alt = lines[idx + 1].strip()
                if alt and len(alt) > 2:
                    taxpayer_name = alt
                    break

    return {
        "tin_number": tin_number,
        "taxpayer_name": taxpayer_name,
        "is_valid_format": is_valid_tin_certificate(text)
    }

def query_ollama(text: str, question: str) -> Optional[str]:
    """Query Ollama for field extraction as fallback"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"Given this TIN document text: {text}\n\n{question}\nRespond with just the answer.",
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
    except:
        pass
    return None

def compare_names(extracted_name: str, verified_name: str) -> Dict[str, Any]:
    """Compare extracted name with verified name"""
    if not extracted_name or not verified_name:
        return {"match": False, "similarity_score": 0, "reason": "Missing name(s)"}
    
    # Normalize names
    def normalize(name):
        return re.sub(r'[^A-Za-z0-9]', '', name.lower().strip())
    
    norm_extracted = normalize(extracted_name)
    norm_verified = normalize(verified_name)
    
    if norm_extracted == norm_verified:
        return {"match": True, "similarity_score": 1.0, "reason": "Exact match"}
    
    # Check for partial match
    similarity = len(set(norm_extracted) & set(norm_verified)) / max(len(norm_extracted), len(norm_verified))
    if similarity >= 0.8:
        return {"match": True, "similarity_score": similarity, "reason": "High similarity"}
    
    return {"match": False, "similarity_score": similarity, "reason": "Low similarity"}

def extract_and_verify_tin(image_path: str) -> Dict[str, Any]:
    """Main function to extract and verify TIN certificate"""
    qoreid_client = QoreIDClient()
    
    try:
        # Step 1: OCR text extraction
        text = detect_text_from_image(image_path)
        print(f"format, {text}")
        
        # Step 2: Validate document format
        if not is_valid_tin_certificate(text):
            return {
                "error": "Invalid TIN certificate format",
                "verification_status": "invalid_document_format"
            }
        
        # Step 3: Extract fields
        extracted_data = extract_tin_fields(text)
        
        # Fallback to Ollama if extraction failed
        if not extracted_data["tin_number"]:
            ollama_tin = query_ollama(text, "What is the TIN number from this document?")
            if ollama_tin:
                extracted_data["tin_number"] = re.search(r'[0-9-]+', ollama_tin).group()
        
        if not extracted_data["taxpayer_name"]:
            ollama_name = query_ollama(text, "What is the taxpayer name from this document?")
            if ollama_name:
                extracted_data["taxpayer_name"] = ollama_name
        
        if not extracted_data["tin_number"]:
            return {
                "error": "Could not extract TIN number",
                "verification_status": "extraction_failed"
            }
        
        # Prepare result
        result = {
            "tin_number": extracted_data["tin_number"],
            "taxpayer_name": extracted_data["taxpayer_name"],
            "document_valid": extracted_data["is_valid_format"],
            "verification_status": "not_verified",
            "verification_details": {
                "document_validation": {
                    "passed": extracted_data["is_valid_format"],
                    "message": "Document appears to be a valid TIN certificate" 
                             if extracted_data["is_valid_format"] 
                             else "Document format doesn't match TIN certificate"
                }
            }
        }
        
        # Step 4: Verify with QoreID
        if extracted_data["tin_number"]:
            verification_response = qoreid_client.verify_tin(extracted_data["tin_number"])
            
            if verification_response and "error" not in verification_response:
                verified_name = verification_response.get("taxpayer", {}).get("name", "").strip()
                name_comparison = compare_names(extracted_data["taxpayer_name"], verified_name)
                
                result.update({
                    "verification_status": "verified" if name_comparison["match"] else "verification_failed",
                    "verification_details": {
                        **result["verification_details"],
                        "api_response": verification_response,
                        "name_match": name_comparison,
                        "verification_checks": {
                            "document_valid": extracted_data["is_valid_format"],
                            "name_matches": name_comparison["match"],
                            "api_verified": True
                        },
                        "overall_validity": all([
                            extracted_data["is_valid_format"],
                            name_comparison["match"]
                        ])
                    }
                })
                
            elif verification_response and "error" in verification_response:
                result.update({
                    "verification_status": "verification_failed",
                    "verification_details": {
                        **result["verification_details"],
                        "error": verification_response["error"],
                        "verification_checks": {
                            "document_valid": extracted_data["is_valid_format"],
                            "name_matches": False,
                            "api_verified": False
                        }
                    }
                })
            else:
                result.update({
                    "verification_status": "verification_unavailable",
                    "verification_details": {
                        **result["verification_details"],
                        "error": "QoreID service unavailable",
                        "verification_checks": {
                            "document_valid": extracted_data["is_valid_format"],
                            "name_matches": False,
                            "api_verified": False
                        }
                    }
                })
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "verification_status": "processing_error"
        }