# ai/compliance/engine.py

import os
from compliance.models import ComplianceCheck
from bids.models import BidDocument, Bid
from tenders.models import Tender

from ai.services.bid_parser import parse_bid_document
from ai.services.cac_parser import extract_cac_fields
from ai.services.tin_parser import extract_and_verify_tin
from ai.services.tcc_parser import extract_and_verify_tcc
from ai.services.iso_pecb_parser import extract_and_verify_pecb
from notifications.utils import notify_user

def run_compliance_check(bid):
    tender: Tender = bid.tender
    required_docs = tender.required_documents
    documents = bid.documents.all()

    result = {
        "missing_documents": [],
        "failed_documents": [],
        "document_scores": {},
        "proposal_score": 0,
        "notes": "",
        "evaluation": {}
    }

    # 1. Check for missing documents
    doc_types_present = [doc.document_type for doc in documents]
    for required in required_docs:
        if required not in doc_types_present:
            result["missing_documents"].append(required)

    # 2. Run parsers for known types
    for doc in documents:
        doc_path = doc.file.path
        doc_type = doc.document_type.upper()

        try:
            if doc_type == "CAC":
                parsed = extract_cac_fields(doc_path)

            elif doc_type == "TIN":
                parsed = extract_and_verify_tin(doc_path)

            elif doc_type == "TCC":
                parsed = extract_and_verify_tcc(doc_path)

            elif doc_type == "ISO_PECB":
                parsed = extract_and_verify_pecb(doc_path)

            elif doc_type == "BID":
                parsed = parse_bid_document(
                    bid_file_path=doc_path,
                    tender=tender,
                )
                doc.extracted_data = parsed
                doc.verification_status = "verified" if parsed["score"] >= 60 else "failed"
                doc.save()
                result["proposal_score"] = parsed["score"]
                result["evaluation"] = parsed.get("evaluation", {})
                continue  # Skip common verification logic for BID

            else:
                continue  # Unknown or unsupported type for now

            # Common logic for CAC, TIN, TCC, ISO_PECB
            doc.extracted_data = parsed
            doc.verification_status = parsed.get("verification_status", "failed")
            doc.save()

            if parsed.get("verification_status") == "verified":
                result["document_scores"][doc_type] = 100
            else:
                result["failed_documents"].append(doc_type)
                result["document_scores"][doc_type] = 50

        except Exception as e:
            result["failed_documents"].append(doc_type)
            result["document_scores"][doc_type] = 0
            doc.extracted_data = {"error": str(e)}
            doc.verification_status = "error"
            doc.save()

    # 3. Determine overall compliance
    passed = (
        not result["missing_documents"]
        and len(result["failed_documents"]) == 0
        and result["proposal_score"] >= 60
    )

    # 4. Save result
    compliance, _ = ComplianceCheck.objects.update_or_create(
        bid=bid,
        defaults={
            "is_compliant": passed,
            "missing_documents": result["missing_documents"],
            "failed_documents": result["failed_documents"],
            "document_scores": result["document_scores"],
            "proposal_score": result["proposal_score"],
            "notes": "Auto-generated compliance evaluation",
            "evaluation": result["evaluation"]
        }
    )

    # Compute average document score
    doc_scores = list(result["document_scores"].values())
    avg_doc_score = sum(doc_scores) / len(doc_scores) if doc_scores else 0

    # Combine with proposal score (e.g., 70% proposal, 30% docs)
    final_score = 0.7 * result["proposal_score"] + 0.3 * avg_doc_score

    # Save to Bid
    bid.score = round(final_score, 2)
    bid.save()

    return compliance

def rank_bids_for_tender(tender_id):
    bids = Bid.objects.filter(tender_id=tender_id, score__isnull=False).order_by('-score')

    for index, bid in enumerate(bids, start=1):
        bid.rank = index
        bid.save()

    notify_user(
        recipient=tender.created_by,
        message=f"All bids for your tender '{tender.title}' have been processed and ranked.",
        data={"type": "tender_ranking", "tender_id": tender.id}
    )
