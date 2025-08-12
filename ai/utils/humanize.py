# ai/utils/humanize.py
def humanize_doc_result(doc):
    """Return a short, human-friendly summary for a BidDocument."""
    data = doc.extracted_data or {}
    doc_type = (doc.document_type or "").upper()
    status = doc.verification_status  # "pending" | "verified" | "failed"
    verdict = "⏳ Pending"
    if status == "verified":
        verdict = "✅ Verified"
    elif status == "failed":
        verdict = "❌ Failed"

    # Common helpers
    details = (data.get("verification_details") or {})
    checks = (details.get("verification_checks") or {})

    # Per-type formatting
    if doc_type == "TIN":
        tin = data.get("tin_number") or data.get("tin") or "—"
        name = data.get("taxpayer_name") or data.get("name") or "—"
        doc_valid = "Yes" if data.get("document_valid") else "No"
        api_verified = "Yes" if checks.get("api_verified") else "No"
        name_matches = "Yes" if checks.get("name_matches") else "No"
        err = details.get("error")

        lines = [
            f"TIN: {tin}",
            f"Taxpayer Name: {name}",
            f"Document Valid: {doc_valid}",
            f"API Verified: {api_verified}",
            f"Name Matches: {name_matches}",
        ]
        if err:
            lines.append(f"Issue: {err}")

        header = f"{verdict} — TIN Certificate"
        return header + "\n" + "\n".join(f"• {l}" for l in lines)

    if doc_type == "CAC":
        rc = (data.get("rc") or data.get("rc_number") or "—")
        company = data.get("company_name") or data.get("name") or "—"
        inc_date = data.get("incorporation_date") or "—"
        header = f"{verdict} — CAC Document"
        lines = [f"Company: {company}", f"RC/BN: {rc}", f"Incorporation Date: {inc_date}"]
        if details.get("error"): lines.append(f"Issue: {details['error']}")
        return header + "\n" + "\n".join(f"• {l}" for l in lines)

    if doc_type == "TCC":
        tcc_no = data.get("tcc_number") or "—"
        valid_from = data.get("valid_from") or "—"
        valid_to = data.get("valid_to") or "—"
        header = f"{verdict} — Tax Clearance Certificate"
        lines = [f"TCC No: {tcc_no}", f"Valid: {valid_from} → {valid_to}"]
        if details.get("error"): lines.append(f"Issue: {details['error']}")
        return header + "\n" + "\n".join(f"• {l}" for l in lines)

    if doc_type == "ISO_PECB":
        cert_no = data.get("certificate_number") or "—"
        std = data.get("standard") or "—"
        header = f"{verdict} — ISO/PECB Certificate"
        lines = [f"Certificate: {cert_no}", f"Standard: {std}"]
        if details.get("error"): lines.append(f"Issue: {details['error']}")
        return header + "\n" + "\n".join(f"• {l}" for l in lines)

    if doc_type == "TECHNICAL_PROPOSAL":
        score = data.get("score")
        evaluation = data.get("evaluation")
        header = f"{verdict} — Technical Proposal"
        lines = []
        if score is not None:
            lines.append(f"Score: {score}")
        if isinstance(evaluation, dict) and evaluation:
            # show 2–3 key bullets if present
            for k, v in list(evaluation.items())[:3]:
                lines.append(f"{k.replace('_',' ').title()}: {v}")
        if details.get("error"): lines.append(f"Issue: {details['error']}")
        return header + ("\n" + "\n".join(f"• {l}" for l in lines) if lines else "")

    # Fallback generic
    header = f"{verdict} — {doc_type or 'Document'}"
    err = details.get("error")
    body = f"\n• Issue: {err}" if err else ""
    return header + body
