import os
import re
from os import listdir
from os.path import isfile, join, exists
import time
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'bidflow-466722-ef0519222bd5.json'
from google.cloud import vision


class QoreIDClient:
    """QoreID API client for CAC verification"""
    
    def __init__(self):
        self.base_url = "https://api.qoreid.com"
        self.client_id = "N1UHQOW3PDNPK1B31X6P"
        self.secret = "17476cbb1aff42be9e835913b02b4410"
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self) -> Optional[str]:
        """Get or refresh access token"""
        # Check if current token is still valid
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at - timedelta(minutes=5)):
            return self.access_token
        
        try:
            url = f"{self.base_url}/token"
            payload = {
                "clientId": self.client_id,
                "secret": self.secret
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code in (200, 201):
                data = response.json()
                self.access_token = data.get("accessToken")
                expires_in = data.get("expiresIn", 7200)  # Default 2 hours
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                print(f"✅ Successfully obtained QoreID access token")
                return self.access_token
            else:
                print(f"❌ Failed to get QoreID token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting QoreID token: {str(e)}")
            return None
    
    def verify_cac(self, registration_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Verify CAC registration number (both BN and RC) and get company details"""
        if not registration_info or not registration_info.get("full_number"):
            return None
            
        token = self.get_access_token()
        if not token:
            return None
        
        try:
            url = f"{self.base_url}/v1/ng/identities/cac-basic"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "regNumber": registration_info["full_number"]  # Already has BN or RC prefix
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Successfully verified {registration_info['type']} number: {registration_info['full_number']}")
                return data
            elif response.status_code == 404:
                print(f"❌ {registration_info['type']} number not found: {registration_info['full_number']}")
                return {"error": f"{registration_info['type']} number not found in database"}
            else:
                print(f"❌ {registration_info['type']} verification failed: {response.status_code} - {response.text}")
                return {"error": f"Verification failed: {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Error verifying {registration_info['type']}: {str(e)}")
            return {"error": f"Verification error: {str(e)}"}

def detect_text(path):
    """Extract text from image using Google Cloud Vision API"""
    client = vision.ImageAnnotatorClient()
    with open(path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    if not texts:
        return "No text detected"
    
    if response.error.message:
        raise Exception(
            "{}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors".format(response.error.message)
        )
    return texts[0].description

def extract_registration_number(text):
    """Extract registration number and determine if it's BN or RC"""
    registration_info = {
        "number": None,
        "type": None,  # "BN" for business name, "RC" for company registration
        "full_number": None  # BN123456 or RC123456
    }
    
    # Check for business name registration first
    business_name_indicators = [
        r'registered as a business name',
        r'business name registration',
        r'CRBN\s*[:#-]?\s*(\d+)',
        r'business name.*?(\d{4,7})',
        r'(\d{4,7}).*?business name'
    ]
    
    for pattern in business_name_indicators:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Extract number from match
            if 'CRBN' in pattern:
                number = match.group(1)
            else:
                # Look for numbers in the matched text or nearby
                numbers = re.findall(r'\b(\d{4,7})\b', match.group(0))
                if numbers:
                    number = numbers[0]
                elif len(match.groups()) > 0:
                    number = match.group(1)
                else:
                    continue
            
            registration_info["number"] = number
            registration_info["type"] = "BN"
            registration_info["full_number"] = f"BN{number}"
            return registration_info
    
    # If not business name, check for company registration patterns
    company_patterns = [
        # Pattern 1: COMPANY REGISTRATION NO. 1924691
        (r'COMPANY REGISTRATION NO\.?\s*(\d+)', 1),
        
        # Pattern 2: CAC/IT/NO 64997 (Incorporated Trustees)
        (r'CAC/IT/NO\s*(\d+)', 1),
        
        # Pattern 3: RC NO. or REGISTRATION NUMBER
        (r'(?:RC\s*NO\.?|REGISTRATION\s*NUMBER)\s*[:#-]?\s*(\d+)', 1),
        
        # Pattern 4: Just CAC followed by number (more general)
        (r'CAC\s*[/#-]?\s*(\d{4,})', 1),
        
        # Pattern 5: Certificate of Incorporation context
        (r'Certificate of Incorporation.*?(\d{4,7})', 1),
        
        # Pattern 6: Look for RC prefix directly
        (r'RC\s*[:#-]?\s*(\d+)', 1)
    ]
    
    for pattern, group_idx in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = match.group(group_idx)
            registration_info["number"] = number
            registration_info["type"] = "RC"
            registration_info["full_number"] = f"RC{number}"
            return registration_info
    
    # Pattern 7: Look for any 4-7 digit number near CAC-related keywords
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Check for business name context first
        if re.search(r'business name', line, re.IGNORECASE):
            for j in range(max(0, i-1), min(len(lines), i+3)):
                numbers = re.findall(r'\b(\d{4,7})\b', lines[j])
                if numbers:
                    registration_info["number"] = numbers[0]
                    registration_info["type"] = "BN"
                    registration_info["full_number"] = f"BN{numbers[0]}"
                    return registration_info
        
        # Check for general CAC/registration context
        elif re.search(r'(?:CAC|REGISTRATION|INCORPORATION|CERTIFICATE)', line, re.IGNORECASE):
            for j in range(max(0, i-1), min(len(lines), i+3)):
                numbers = re.findall(r'\b(\d{4,7})\b', lines[j])
                if numbers:
                    registration_info["number"] = numbers[0]
                    registration_info["type"] = "RC"  # Default to RC if context unclear
                    registration_info["full_number"] = f"RC{numbers[0]}"
                    return registration_info
    
    return registration_info

def extract_company_name(text):
    """Extract company name using multiple strategies"""
    # Normalize spaces
    normalized_text = re.sub(r'[ ]+', ' ', text)

    # Strategy 1: For trustee documents - Look for "Trustees of [ORGANIZATION NAME]"
    trustee_patterns = [
        r'Trustees of\s+([A-Z\s]+?)(?:\s+have|\s+are|\s+is|\n|$)',
        r'Incorporated Trustees of\s+([A-Z\s]+?)(?:\s+have|\s+are|\s+is|\n|$)',
        r'duly appointed Trustees of\s+([A-Z\s]+?)(?:\s+have|\s+are|\s+is|\n|$)'
    ]
    
    for pattern in trustee_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company_name = match.group(1).strip()
            # Clean up the company name
            company_name = re.sub(r'[,\s]+$', '', company_name)
            if company_name and len(company_name) > 2:  # Ensure it's not just whitespace or too short
                return company_name

    # Strategy 2: After "hereby certify that" (for non-trustee documents)
    match = re.search(r'(?:hereby|to) certif(?:y|ies)? that\s+(.+?)(?:\s+(?:is|are|have)|,|\n)', normalized_text, re.IGNORECASE | re.DOTALL)
    if match:
        potential_name = match.group(1).strip()
        # Check if this contains trustee information (names with titles like MR., ENGR., etc.)
        if not re.search(r'\b(?:MR\.?|MRS\.?|MS\.?|DR\.?|PROF\.?|ENGR\.?|ENGR\b)\s+[A-Z]+', potential_name, re.IGNORECASE):
            # Clean up the company name
            company_name = re.sub(r'[,\s]+$', '', potential_name)
            # If it's too long, it might include trustees names, so extract just the organization name
            if len(company_name) > 100:
                # Look for organization name pattern
                org_match = re.search(r'(.*?(?:UNION|LIMITED|LTD|COMPANY|CORP|INC|ASSOCIATION|ORGANIZATION|FOUNDATION|TRUST|SOCIETY))', company_name, re.IGNORECASE)
                if org_match:
                    return org_match.group(1).strip()
            return company_name

    # Strategy 3: Look for company name in all caps (excluding common certificate words)
    lines = text.split('\n')
    candidates = []
    
    # Words to exclude when looking for company names
    exclude_words = {
        'CERTIFICATE', 'COMMISSION', 'REPUBLIC', 'AFFAIRS', 'FEDERAL', 'NIGERIA',
        'CORPORATE', 'CAC', 'INCORPORATION', 'TRUSTEES', 'CONDITIONS', 'DIRECTIONS',
        'REGISTRAR', 'GENERAL', 'ABUJA', 'SEAL', 'COMMON'
    }
    
    for line in lines:
        line = line.strip()
        # Look for lines that are likely company names
        if (line.isupper() and 
            5 < len(line) < 100 and 
            not re.match(r'^[A-Z\s]{1,5}$', line) and  # Skip very short lines
            not any(word in line for word in exclude_words) and
            not re.search(r'^(?:MR\.?|MRS\.?|MS\.?|DR\.?|PROF\.?|ENGR\.?)', line)):  # Skip names with titles
            candidates.append(line)
    
    if candidates:
        # Prefer lines with company-like endings
        for candidate in candidates:
            if re.search(r'(?:UNION|LIMITED|LTD|COMPANY|CORP|INC|ASSOCIATION|ORGANIZATION|FOUNDATION|TRUST|SOCIETY)\b', candidate):
                return candidate
        return candidates[0]

    # Strategy 4: Look for organization names mentioned in certificate text
    org_patterns = [
        r'Certificate of Incorporation.*?of\s+(?:the\s+)?(?:Incorporated\s+)?Trustees\s+of\s+([A-Z\s]+?)(?:\n|I\s+hereby)',
        r'(?:the\s+)?(?:Incorporated\s+)?Trustees\s+of\s+([A-Z][A-Z\s]+?)(?:\s+have|\s+are|\s+is)'
    ]
    
    for pattern in org_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            company_name = match.group(1).strip()
            # Clean up and validate
            company_name = re.sub(r'[,\s]+$', '', company_name)
            if company_name and len(company_name) > 2:
                return company_name

    return None

def query_ollama(text, question):
    """Query Ollama for field extraction as fallback"""
    try:
        url = "http://localhost:11434/api/generate"
        prompt = f"""
Given this CAC document text, {question}

Document text:
{text}

Please respond with just the answer, no explanation.
"""
        
        data = {
            "model": "llama3.2",  # or whatever model you have
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
    except:
        pass
    return None

def compare_company_names(extracted_name: str, verified_name: str) -> Dict[str, Any]:
    """Compare extracted company name with verified name from QoreID"""
    if not extracted_name or not verified_name:
        return {
            "match": False,
            "similarity_score": 0,
            "reason": "One or both names are missing"
        }
    
    # Normalize names for comparison
    def normalize_name(name):
        # Remove extra spaces, convert to uppercase, remove common suffixes/prefixes
        normalized = re.sub(r'\s+', ' ', name.upper().strip())
        # Remove common business suffixes for comparison
        normalized = re.sub(r'\s+(LIMITED|LTD|COMPANY|CORP|INC|UNION|ASSOCIATION|ORGANIZATION|FOUNDATION|TRUST|SOCIETY)$', '', normalized)
        return normalized
    
    norm_extracted = normalize_name(extracted_name)
    norm_verified = normalize_name(verified_name)
    
    # Exact match
    if norm_extracted == norm_verified:
        return {
            "match": True,
            "similarity_score": 1.0,
            "reason": "Exact match after normalization"
        }
    
    # Check if one contains the other
    if norm_extracted in norm_verified or norm_verified in norm_extracted:
        return {
            "match": True,
            "similarity_score": 0.8,
            "reason": "Partial match - one name contains the other"
        }
    
    # Calculate word overlap
    extracted_words = set(norm_extracted.split())
    verified_words = set(norm_verified.split())
    
    if not extracted_words or not verified_words:
        return {
            "match": False,
            "similarity_score": 0,
            "reason": "Unable to parse words from names"
        }
    
    overlap = len(extracted_words.intersection(verified_words))
    total_unique = len(extracted_words.union(verified_words))
    similarity_score = overlap / total_unique if total_unique > 0 else 0
    
    # Consider it a match if similarity is high enough
    if similarity_score >= 0.6:
        return {
            "match": True,
            "similarity_score": similarity_score,
            "reason": f"High word similarity ({similarity_score:.1%})"
        }
    
    return {
        "match": False,
        "similarity_score": similarity_score,
        "reason": f"Low similarity ({similarity_score:.1%})"
    }

def extract_cac_fields(image_path):
    """Extract CAC fields from image using Google Cloud Vision with QoreID verification"""
    qoreid_client = QoreIDClient()
    
    try:
        # Use Google Cloud Vision first
        text = detect_text(image_path)
        
        # Extract registration information (number and type)
        registration_info = extract_registration_number(text)
        
        # If no registration number found, try Ollama
        if not registration_info["number"]:
            print("Trying Ollama for registration number...")
            ollama_response = query_ollama(text, "what is the registration number or RC number or BN number?")
            if ollama_response:
                # Try to extract number and determine type from Ollama response
                number_match = re.search(r'(?:BN|RC)?(\d{4,7})', ollama_response)
                if number_match:
                    number = number_match.group(1)
                    # Determine type based on context
                    if re.search(r'business name', ollama_response, re.IGNORECASE):
                        registration_info = {
                            "number": number,
                            "type": "BN",
                            "full_number": f"BN{number}"
                        }
                    else:
                        registration_info = {
                            "number": number,
                            "type": "RC",
                            "full_number": f"RC{number}"
                        }

        company_name = extract_company_name(text)
        
        # If no company name found, try Ollama
        if not company_name:
            print("Trying Ollama for company name...")
            company_name = query_ollama(text, "what is the company name or organization name or business name?")

        # Incorporation date (e.g., "this 21st day of December, 2020")
        date_match = re.search(
            r'this\s+\d{1,2}(?:st|nd|rd|th)?\s+day of\s+[A-Za-z]+,\s+\d{4}',
            text,
            re.IGNORECASE
        )
        date_of_incorp = (
            date_match.group(0).replace("this", "").strip().capitalize()
            if date_match else None
        )
        
        # Alternative date pattern: "Twenty-Eighth day of October, 2013"
        if not date_of_incorp:
            alt_date_match = re.search(
                r'(?:Twenty-|Thirty-|First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth|Nineteenth|[A-Z][a-z]+-?[A-Z]?[a-z]*)\s+day of\s+[A-Za-z]+,\s+\d{4}',
                text,
                re.IGNORECASE
            )
            if alt_date_match:
                date_of_incorp = alt_date_match.group(0).strip().capitalize()

        # Prepare result with extracted data
        result = {
            "rc_number": registration_info["number"],  # Keep backward compatibility
            "registration_number": registration_info["number"],
            "registration_type": registration_info["type"],
            "full_registration_number": registration_info["full_number"],
            "company_name": company_name,
            "date_of_incorporation": date_of_incorp,
            "verification_status": "not_verified",
            "verification_details": {}
        }

        # Verify with QoreID if we have a registration number
        if registration_info["number"]:
            print(f"\n🔍 Verifying {registration_info['type']} Number: {registration_info['full_number']} with QoreID...")
            verification_response = qoreid_client.verify_cac(registration_info)
            
            if verification_response and "error" not in verification_response:
                # Successful verification
                cac_data = verification_response.get("cac", {})
                verified_company_name = cac_data.get("companyName", "").strip()
                verified_reg_number = cac_data.get("rcNumber", "")
                company_status = cac_data.get("status", "")
                registration_date = cac_data.get("registrationDate", "")
                
                # Compare company names
                name_comparison = compare_company_names(company_name, verified_company_name)
                
                result.update({
                    "verification_status": "verified",
                    "verification_details": {
                        "qoreid_response": verification_response,
                        "verified_company_name": verified_company_name,
                        "verified_registration_number": verified_reg_number,
                        "company_status": company_status,
                        "verified_registration_date": registration_date,
                        "name_match": name_comparison,
                        "overall_validity": (
                            name_comparison["match"] and 
                            company_status.upper() == "ACTIVE" and
                            verification_response.get("summary", {}).get("cac_check") == "verified"
                        )
                    }
                })
                
                print(f"✅ Verification successful!")
                print(f"   Verified Company: {verified_company_name}")
                print(f"   Status: {company_status}")
                print(f"   Name Match: {name_comparison['match']} ({name_comparison['similarity_score']:.1%})")
                
            elif verification_response and "error" in verification_response:
                # Verification failed
                result.update({
                    "verification_status": "verification_failed",
                    "verification_details": {
                        "error": verification_response["error"]
                    }
                })
                print(f"❌ Verification failed: {verification_response['error']}")
            else:
                # No response from verification service
                result.update({
                    "verification_status": "verification_unavailable",
                    "verification_details": {
                        "error": "QoreID service unavailable"
                    }
                })
                print(f"⚠️ QoreID service unavailable")
        
        else:
            print("⚠️ No registration number found - skipping verification")
            result["verification_status"] = "no_registration_number"

        return result

    except Exception as e:
        return {
            "error": str(e),
            "verification_status": "extraction_failed"
        }