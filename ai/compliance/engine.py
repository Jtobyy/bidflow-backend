# ai/compliance/engine.py
from compliance.models import ComplianceCheck
from bids.models import Bid, BidDocument
from tenders.models import Tender
from ai.services.bid_parser import parse_bid_document
from ai.services.cac_parser import extract_cac_fields
from ai.services.tin_parser import extract_and_verify_tin
from ai.services.tcc_parser import extract_and_verify_tcc
from ai.services.iso_pecb_parser import extract_and_verify_pecb
from ai.utils.status import normalize_verification_status
from notifications.utils import notify_user

def reverify_document(doc: BidDocument) -> BidDocument:
    """
    Re-run verification for a single document and persist results.
    """
    doc_type = (doc.document_type or "").upper()
    try:
        if doc_type == "CAC":
            parsed = extract_cac_fields(doc.file.path)
        elif doc_type == "TIN":
            parsed = extract_and_verify_tin(doc.file.path)
        elif doc_type == "TCC":
            parsed = extract_and_verify_tcc(doc.file.path)
        elif doc_type == "ISO_PECB":
            parsed = extract_and_verify_pecb(doc.file.path)
        elif doc_type == "TECHNICAL_PROPOSAL":
            # Need tender for context
            parsed = parse_bid_document(bid_file_path=doc.file.path, tender=doc.bid.tender)
        else:
            # No parser yet (FINANCIAL_PROPOSAL/OTHER). Keep pending.
            return doc

        doc.extracted_data = parsed
        doc.verification_status = normalize_verification_status(parsed.get("verification_status", "failed"))
        doc.save(update_fields=["extracted_data", "verification_status"])
        return doc

    except Exception as e:
        doc.extracted_data = {"error": str(e)}
        doc.verification_status = "failed"
        doc.save(update_fields=["extracted_data", "verification_status"])
        return doc

def run_compliance_check(bid: Bid):
    tender: Tender = bid.tender
    required_docs = [str(x).upper() for x in (tender.required_documents or [])]
    documents = bid.documents.all()

    result = {
        "missing_documents": [],
        "failed_documents": [],
        "document_scores": {},
        "proposal_score": 0,
        "notes": "Auto-generated compliance evaluation",
        "evaluation": {},
    }

    # 1) Check missing
    present = [d.document_type.upper() for d in documents]
    for req in required_docs:
        if req not in present:
            result["missing_documents"].append(req)

    # 2) Parse / verify known types
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

            elif doc_type == "TECHNICAL_PROPOSAL":
                parsed = parse_bid_document(bid_file_path=doc_path, tender=tender)
                # ✅ status by score here (not parser string)
                score = parsed.get("score", 0) or 0
                doc.extracted_data = parsed
                doc.verification_status = "verified" if score >= 60 else "failed"
                doc.save(update_fields=["verification_status", "extracted_data"])
                result["proposal_score"] = score
                result["evaluation"] = parsed.get("evaluation", {})
                continue  # skip common logic below

            else:
                # FINANCIAL_PROPOSAL or unsupported — no parser yet
                continue

            # ✅ Common post-parse — normalize once and reuse
            raw = parsed.get("verification_status")
            norm = normalize_verification_status(raw)
            parsed["raw_verification_status"] = raw  # optional: keep raw for debugging

            doc.extracted_data = parsed
            doc.verification_status = norm
            doc.save(update_fields=["verification_status", "extracted_data"])

            if norm == "verified":
                result["document_scores"][doc_type] = 100
            else:
                result["failed_documents"].append(doc_type)
                result["document_scores"][doc_type] = 50

        except Exception as e:
            result["failed_documents"].append(doc_type)
            result["document_scores"][doc_type] = 0
            doc.extracted_data = {"error": str(e)}
            doc.verification_status = "failed"
            doc.save(update_fields=["verification_status", "extracted_data"])

    # 3) Overall compliance
    passed = (
        not result["missing_documents"]
        and len(result["failed_documents"]) == 0
        and result["proposal_score"] >= 60
    )

    # 4) Persist ComplianceCheck (upsert)
    compliance, _ = ComplianceCheck.objects.update_or_create(
        bid=bid,
        defaults={
            "is_compliant": passed,
            "missing_documents": result["missing_documents"],
            "failed_documents": result["failed_documents"],
            "document_scores": result["document_scores"],
            "proposal_score": result["proposal_score"],
            "notes": result["notes"],
            "evaluation": result["evaluation"],
        },
    )

    # 5) Final score & bid status
    doc_scores = list(result["document_scores"].values())
    avg_doc_score = sum(doc_scores) / len(doc_scores) if doc_scores else 0
    final_score = 0.7 * result["proposal_score"] + 0.3 * avg_doc_score

    missing_count = len(result["missing_documents"])
    DISQUALIFY_THRESHOLD = 3  # >2 missing docs → disqualified

    if missing_count >= DISQUALIFY_THRESHOLD:
        new_status = "disqualified"
    elif passed:
        new_status = "reviewed"  # or "accepted" if that's your policy
    else:
        new_status = "rejected"

    bid.score = round(final_score, 2)
    bid.status = new_status
    bid.save(update_fields=["score", "status"])

    return compliance

def rank_bids_for_tender(tender_id: int):
    # Correct filter
    bids = Bid.objects.filter(tender_id=tender_id, score__isnull=False).order_by("-score")
    for idx, b in enumerate(bids, start=1):
        if b.rank != idx:
            b.rank = idx
            b.save(update_fields=["rank"])

    tender = Tender.objects.get(pk=tender_id)
    notify_user(
        recipient=tender.created_by,
        message=f"All bids for your tender '{tender.title}' have been processed and ranked.",
        data={"type": "tender_ranking", "tender_id": tender.id},
    )
