import os
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from .vision_ocr import detect_text_from_image

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'bidflow-466722-ef0519222bd5.json'

class QoreIDClient:
    """QoreID API client for TCC/TIN verification"""
    
    def __init__(self):
        self.base_url = "https://api.qoreid.com"
        self.client_id = "N1UHQOW3PDNPK1B31X6P"
        self.secret = "17476cbb1aff42be9e835913b02b4410"
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self) -> Optional[str]:
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at - timedelta(minutes=5):
            return self.access_token

        try:
            res = requests.post(
                f"{self.base_url}/token",
                json={"clientId": self.client_id, "secret": self.secret},
                timeout=30
            )
            if res.status_code in (200, 201):
                data = res.json()
                self.access_token = data.get("accessToken")
                self.token_expires_at = datetime.now() + timedelta(seconds=data.get("expiresIn", 7200))
                return self.access_token
        except:
            return None
    
    def verify_tin(self, tin_number: str) -> Optional[Dict[str, Any]]:
        token = self.get_access_token()
        if not token:
            return None
        try:
            res = requests.get(
                f"{self.base_url}/v2/ng/identities/tin/{tin_number}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            return res.json() if res.status_code == 200 else {"error": res.text}
        except Exception as e:
            return {"error": str(e)}

def is_valid_tcc_certificate(text: str) -> bool:
    """Check if OCR result resembles a TCC format"""
    keywords = [
        r'TAX\s+CLEARANCE\s+CERTIFICATE',
        r'FIRS',
        r'TCC\s*NO',
        r'RC\s*No',
        r'\bTIN\b',
        r'Name\s+of\s+Company',
        r'Commenced\s+Business',
        r'Source\s+of\s+Income',
        r'This Certificate Expires on'
    ]
    matched = sum(1 for pattern in keywords if re.search(pattern, text, re.IGNORECASE))
    return matched >= 6

def is_certificate_expired(expiration_date: str) -> bool:
    """Check if the certificate has expired"""
    if not expiration_date:
        return False
    
    try:
        exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
        current_date = datetime.now()
        return current_date > exp_date
    except ValueError:
        print(f"DEBUG: Invalid date format: {expiration_date}")
        return False

def extract_tcc_fields(text: str) -> Dict[str, str]:
    """Extract fields like TIN, taxpayer name, RC number, expiration date"""
    print(f"DEBUG: Processing text:\n{text}")
    
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    tin_number, taxpayer_name, rc_number, expiration_date = None, None, None, None

    # First, try to find TIN anywhere in the text with a more flexible pattern
    tin_patterns = [
        r'\b(\d{8}-\d{4})\b',  # 8 digits, hyphen, 4 digits
        r'TIN\s*[:#-]?\s*(\d{8}-\d{4})',  # TIN followed by the number
        r'TIN.*?(\d{8}-\d{4})',  # TIN somewhere before the number
    ]
    
    for pattern in tin_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            tin_number = matches[0]
            print(f"DEBUG: Found TIN using pattern '{pattern}': {tin_number}")
            break

    # Find label positions for tabular OCR format
    label_positions = {}
    for i, line in enumerate(lines):
        if re.search(r'Name of Company', line, re.IGNORECASE):
            label_positions['company_name'] = i
        elif re.search(r'RC\s*No', line, re.IGNORECASE):
            label_positions['rc_no'] = i
        elif re.search(r'\bTIN\b', line, re.IGNORECASE):
            label_positions['tin'] = i
        elif re.search(r'Date of Incorporation', line, re.IGNORECASE):
            label_positions['incorporation'] = i
        elif re.search(r'Business Address', line, re.IGNORECASE):
            label_positions['address'] = i
        elif re.search(r'This Certificate Expires on', line, re.IGNORECASE):
            label_positions['expiration'] = i

    print(f"DEBUG: Found label positions: {label_positions}")

    # Extract company name based on tabular format
    if 'company_name' in label_positions:
        company_label_pos = label_positions['company_name']
        for i in range(company_label_pos + 1, min(len(lines), company_label_pos + 15)):
            line = lines[i]
            print(f"DEBUG: Checking line {i} for company name: '{line}'")
            if line.startswith(':') and re.search(r'[A-Za-z]', line):
                potential_name = line[1:].strip()
                if len(potential_name) > 3 and not re.match(r'^\d+(-\d+)*$', potential_name):
                    taxpayer_name = potential_name
                    # Check if next line continues the name
                    if i + 1 < len(lines) and not lines[i + 1].startswith(':'):
                        next_line = lines[i + 1].strip()
                        if next_line and re.search(r'[A-Za-z]', next_line):
                            taxpayer_name += ' ' + next_line
                    print(f"DEBUG: Extracted company name: '{taxpayer_name}'")
                    break

    # Extract RC number based on tabular format
    if 'rc_no' in label_positions:
        rc_label_pos = label_positions['rc_no']
        for i in range(rc_label_pos + 1, min(len(lines), rc_label_pos + 10)):
            line = lines[i]
            print(f"DEBUG: Checking line {i} for RC number: '{line}'")
            if line.startswith(':'):
                potential_rc = line[1:].strip()
                if re.match(r'^\d+$', potential_rc):
                    rc_number = potential_rc
                    print(f"DEBUG: Extracted RC number: '{rc_number}'")
                    break

    # Extract expiration date based on tabular format
    if 'expiration' in label_positions:
        exp_label_pos = label_positions['expiration']
        for i in range(exp_label_pos + 1, min(len(lines), exp_label_pos + 10)):
            line = lines[i]
            print(f"DEBUG: Checking line {i} for expiration date: '{line}'")
            if line.startswith(':'):
                potential_date = line[1:].strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}$', potential_date):
                    expiration_date = potential_date
                    print(f"DEBUG: Extracted expiration date: '{expiration_date}'")
                    break

    # Fallback patterns for missing fields
    if not taxpayer_name:
        company_match = re.search(r'Name of Company.*?:\s*([A-Z\s]+(?:LIMITED|LTD|COMPANY|CORP|INC))', text, re.IGNORECASE | re.DOTALL)
        if company_match:
            taxpayer_name = company_match.group(1).strip()
            print(f"DEBUG: Extracted company name via fallback pattern: '{taxpayer_name}'")

    if not rc_number:
        rc_match = re.search(r'RC\s*No.*?:\s*(\d+)', text, re.IGNORECASE | re.DOTALL)
        if rc_match:
            rc_number = rc_match.group(1)
            print(f"DEBUG: Extracted RC number via fallback pattern: '{rc_number}'")

    if not expiration_date:
        exp_match = re.search(r'This Certificate Expires on.*?:\s*(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE | re.DOTALL)
        if exp_match:
            expiration_date = exp_match.group(1)
            print(f"DEBUG: Extracted expiration date via fallback pattern: '{expiration_date}'")

    print(f"DEBUG: Final extraction results:")
    print(f"  TIN: {tin_number}")
    print(f"  Name: {taxpayer_name}")
    print(f"  RC: {rc_number}")
    print(f"  Expiration: {expiration_date}")

    return {
        "tin_number": tin_number,
        "taxpayer_name": taxpayer_name,
        "rc_number": rc_number,
        "expiration_date": expiration_date,
        "is_valid_format": is_valid_tcc_certificate(text)
    }

def query_ollama(text: str, question: str) -> Optional[str]:
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": f"Given this TCC document text: {text}\n\n{question}", "stream": False},
            timeout=30
        )
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except:
        return None

def normalize_name(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9]', '', name.lower())

def compare_names(extracted: str, verified: str) -> Dict[str, Any]:
    if not extracted or not verified:
        return {"match": False, "similarity_score": 0, "reason": "Missing names"}
    
    n1, n2 = normalize_name(extracted), normalize_name(verified)
    if n1 == n2:
        return {"match": True, "similarity_score": 1.0, "reason": "Exact match"}
    
    sim = len(set(n1) & set(n2)) / max(len(n1), len(n2))
    return {"match": sim >= 0.8, "similarity_score": sim, "reason": "High similarity" if sim >= 0.8 else "Low similarity"}

def extract_and_verify_tcc(image_path: str) -> Dict[str, Any]:
    try:
        text = detect_text_from_image(image_path)
        print(f"text is {text}")
        extracted = extract_tcc_fields(text)
        
        if not extracted["is_valid_format"]:
            return {
                "error": "Invalid TCC format",
                "verification_status": "invalid_document_format"
            }

        # Check if certificate has expired
        if extracted["expiration_date"] and is_certificate_expired(extracted["expiration_date"]):
            return {
                "error": "Certificate has expired",
                "verification_status": "expired_certificate",
                "expiration_date": extracted["expiration_date"],
                "tin_number": extracted["tin_number"],
                "taxpayer_name": extracted["taxpayer_name"],
                "rc_number": extracted["rc_number"]
            }

        # Enhanced fallbacks for missing fields
        if not extracted["tin_number"]:
            print("DEBUG: TIN not found, trying Ollama fallback...")
            guess = query_ollama(text, "What is the TIN number? Look for a pattern like 8 digits, hyphen, 4 digits (e.g., 12345678-1234)")
            if guess:
                print(f"DEBUG: Ollama response for TIN: {guess}")
                m = re.search(r'\b(\d{8}-\d{4})\b', guess)
                if m:
                    extracted["tin_number"] = m.group(1)
                    print(f"DEBUG: Extracted TIN from Ollama: {extracted['tin_number']}")

        if not extracted["taxpayer_name"]:
            print("DEBUG: Name not found, trying Ollama fallback...")
            guess = query_ollama(text, "What is the company name or taxpayer name?")
            if guess:
                print(f"DEBUG: Ollama response for name: {guess}")
                extracted["taxpayer_name"] = guess.strip()

        if not extracted["tin_number"]:
            return {"error": "TIN not found", "verification_status": "extraction_failed"}

        result = {
            "tin_number": extracted["tin_number"],
            "taxpayer_name": extracted["taxpayer_name"],
            "rc_number": extracted["rc_number"],
            "expiration_date": extracted["expiration_date"],
            "document_valid": extracted["is_valid_format"],
            "verification_status": "not_verified"
        }

        # Verify via API
        qore = QoreIDClient()
        res = qore.verify_tin(extracted["tin_number"])

        if res and "error" not in res:
            verified_name = res.get("tin", {}).get("taxpayerName", "").strip()
            name_match = compare_names(extracted["taxpayer_name"], verified_name)

            result.update({
                "verification_status": "verified" if name_match["match"] else "verification_failed",
                "verification_details": {
                    "api_response": res,
                    "name_match": name_match,
                    "overall_validity": name_match["match"] and extracted["is_valid_format"]
                }
            })
        else:
            result.update({
                "verification_status": "verification_failed",
                "verification_details": {
                    "error": res.get("error") if res else "No response from API"
                }
            })

        return result

    except Exception as e:
        return {"error": str(e), "verification_status": "processing_error"}