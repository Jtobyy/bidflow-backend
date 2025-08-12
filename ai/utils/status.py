# ai/utils/status.py
def normalize_verification_status(raw):
    raw = (raw or "").lower().strip()
    if raw in {"verified", "verification_passed", "valid"}:
        return "verified"
    if raw in {"failed", "verification_failed", "expired_certificate", "error"}:
        return "failed"
    if raw in {"pending", "analyzed", ""}:
        return "pending"
    # default: be conservative
    return "failed"
