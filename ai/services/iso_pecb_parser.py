import os
import re
from datetime import datetime
from typing import Dict, Any
from .vision_ocr import detect_text_from_image
from .pecb_verifier import verify_pecb_certificate  # Import your live verifier

def is_valid_pecb_certificate(text: str) -> bool:
    keywords = [
        r'Professional Evaluation and Certification Board',
        r'PECB',
        r'Certificate Number',
        r'Issue Date',
        r'having met all the certification requirements',
        r'Carolina Cabezas'
    ]
    return sum(1 for pattern in keywords if re.search(pattern, text, re.IGNORECASE)) >= 4

def extract_pecb_fields(text: str) -> Dict[str, Any]:
    print(f"DEBUG: Raw OCR text:\n{text}")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    recipient_name, certificate_title = None, None
    certificate_number, issue_date, validity_years, issuer = None, None, None, None

    # Extract recipient name    
    for i, line in enumerate(lines):
        if re.search(r"hereby attests that", line, re.IGNORECASE) and i + 1 < len(lines):
            candidate = lines[i + 1]
            if re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', candidate):  # Basic full name format
                recipient_name = candidate
                break


    # Extract certificate title
    title_patterns = [
        r'PECB Certified (ISO(?:/IEC)?[\d: ]+.*)',
        r'Certificate Holder in (ISO(?:/IEC)?[\d: ]+.*)',
        r'ISO(?:/IEC)?[\d: ]+.*Foundation',
    ]
    for pattern in title_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            certificate_title = match.group(0).strip()
            print(f"DEBUG: Extracted certificate title: {certificate_title}")
            break

    # Extract certificate number and infer issue date
    match = re.search(r'Certificate Number[:\s]*([A-Z]{3,5}\d{6,}-\d{4}-\d{2})', text)
    if match:
        certificate_number = match.group(1).strip()
        print(f"DEBUG: Extracted certificate number: {certificate_number}")

        # Fallback issue date from cert number
        if not issue_date:
            date_part = certificate_number.split("-")[-2:]
            issue_date = f"{date_part[0]}-{date_part[1]}"
            print(f"DEBUG: Inferred issue date from certificate number: {issue_date}")

    # Optional: Extract explicit issue date
    match = re.search(r'Issue Date[:\s]*([\d]{4}-[\d]{2}-[\d]{2})', text)
    if match:
        issue_date = match.group(1)
        print(f"DEBUG: Extracted issue date: {issue_date}")

    # Validity
    if re.search(r'valid for three years', text, re.IGNORECASE):
        validity_years = '3'
    elif re.search(r'does not expire', text, re.IGNORECASE):
        validity_years = 'no expiry'

    # Issuer
    if re.search(r'Carolina Cabezas', text, re.IGNORECASE):
        issuer = 'Carolina Cabezas'

    return {
        "recipient_name": recipient_name,
        "certificate_title": certificate_title,
        "certificate_number": certificate_number,
        "issue_date": issue_date,
        "validity_years": validity_years,
        "issuer": issuer,
        "is_valid_format": is_valid_pecb_certificate(text)
    }

def extract_and_verify_pecb(image_path: str) -> Dict[str, Any]:
    try:
        text = detect_text_from_image(image_path)
        extracted = extract_pecb_fields(text)

        if not extracted["is_valid_format"]:
            return {
                "error": "Invalid PECB certificate format",
                "verification_status": "invalid_document_format"
            }

        if not extracted["certificate_number"]:
            return {
                "error": "Certificate number not found",
                "verification_status": "extraction_failed"
            }

        # Infer last name from full name
        cert_number = extracted["certificate_number"]
        recipient_name = extracted.get("recipient_name") or ""
        last_name = recipient_name.split()[-1] if recipient_name else ""

        if not last_name:
            return {
                **extracted,
                "verification_status": "verification_failed",
                "verification_details": {"error": "Could not infer last name from certificate"}
            }

        # Verify using headless browser
        verification = verify_pecb_certificate(cert_number, last_name)

        if "error" in verification or "status" not in verification:
            return {
                **extracted,
                "verification_status": "verification_failed",
                "verification_details": verification
            }

        return {
            **extracted,
            "verification_status": "verified",
            "verification_details": verification
        }

    except Exception as e:
        return {"error": str(e), "verification_status": "processing_error"}
