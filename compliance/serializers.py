# compliance/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import ComplianceCheck

DOC_LABELS = {
    "TECHNICAL_PROPOSAL": "Technical Proposal",
    "FINANCIAL_PROPOSAL": "Financial Proposal",
    "CAC": "CAC Certificate",
    "TIN": "Tax Identification (TIN)",
    "TCC": "Tax Clearance Certificate (TCC)",
    "ISO_PECB": "ISO (PECB)",
    "OTHER": "Other",
}

class ComplianceCheckSerializer(serializers.ModelSerializer):
    report_text = serializers.SerializerMethodField()
    outcome_label = serializers.SerializerMethodField()
    last_run_at = serializers.SerializerMethodField()
    documents_brief = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceCheck
        fields = [
            "id",
            "bid",
            "is_compliant",
            "missing_documents",
            "failed_documents",
            "document_scores",
            "evaluation",
            "proposal_score",
            "notes",
            "verified_at",
            # extras
            "outcome_label",
            "last_run_at",
            "documents_brief",
            "report_text",
        ]

    def _label(self, key):
        return DOC_LABELS.get(str(key).upper(), str(key).replace("_", " ").title())

    def get_outcome_label(self, obj):
        return "COMPLIANT ✅" if obj.is_compliant else "NOT COMPLIANT ❌"

    def get_last_run_at(self, obj):
        # Keep frontend formatting simple: return ISO in local time
        if not obj.verified_at:
            return None
        return timezone.localtime(obj.verified_at).isoformat()

    def get_documents_brief(self, obj):
        """
        Quick digest for cards/lists:
        [
          {"type": "CAC", "label": "CAC Certificate", "required": True, "provided": True, "status": "verified", "score": 100},
          {"type": "TIN", "label": "Tax Identification (TIN)", "required": True, "provided": True, "status": "failed", "score": 50},
          {"type": "ISO_PECB", "label": "ISO (PECB)", "required": True, "provided": False, "status": "missing", "score": None},
          ...
        ]
        """
        bid = obj.bid
        tender = bid.tender
        req = [str(x).upper() for x in (tender.required_documents or [])]
        provided = [d.document_type.upper() for d in bid.documents.all()]
        scores = obj.document_scores or {}

        brief = []
        for t in req:
            status = "verified" if scores.get(t, 0) == 100 else (
                "failed" if t in (obj.failed_documents or []) else (
                    "missing" if t not in provided else "pending"
                )
            )
            brief.append({
                "type": t,
                "label": self._label(t),
                "required": True,
                "provided": t in provided,
                "status": status,
                "score": scores.get(t),
            })
        # Optionally show extra (non-required) docs that were uploaded
        extra = [p for p in provided if p not in req]
        for t in extra:
            status = "verified" if scores.get(t, 0) == 100 else (
                "failed" if t in (obj.failed_documents or []) else "pending"
            )
            brief.append({
                "type": t,
                "label": self._label(t),
                "required": False,
                "provided": True,
                "status": status,
                "score": scores.get(t),
            })
        return brief

    def get_report_text(self, obj: ComplianceCheck) -> str:
        bid = obj.bid
        tender = bid.tender
        company = getattr(bid.submitted_by, "company", None)

        # Pretty parts
        missing = ", ".join(self._label(d) for d in (obj.missing_documents or [])) or "None"
        failed = ", ".join(self._label(d) for d in (obj.failed_documents or [])) or "None"
        scores = obj.document_scores or {}
        scores_pretty = ", ".join(f"{self._label(k)}: {v}" for k, v in scores.items()) or "None"
        final_score = f"{bid.score}" if bid.score is not None else "N/A"
        rank = f"#{bid.rank}" if bid.rank else "N/A"
        outcome = "COMPLIANT ✅" if obj.is_compliant else "NOT COMPLIANT ❌"

        # Evaluation highlights
        evaluation = obj.evaluation or {}
        eval_snippets = []
        for k in ("strengths", "weaknesses", "risks", "recommendations"):
            if evaluation.get(k):
                label = k.replace("_", " ").title()
                val = evaluation[k]
                if isinstance(val, list):
                    eval_snippets.append(f"{label}:\n  - " + "\n  - ".join(map(str, val)))
                else:
                    eval_snippets.append(f"{label}: {val}")
        eval_block = ("\n\n" + "\n\n".join(eval_snippets)) if eval_snippets else ""

        submitted_at = timezone.localtime(bid.submitted_at).strftime('%Y-%m-%d %H:%M')
        lines = [
            f"Bid ID: {bid.id}",
            f"Tender: {tender.title} (#{tender.id})",
            f"Company: {getattr(company, 'name', None) or bid.submitted_by.username}",
            f"Submitted At: {submitted_at}",
            "",
            f"Outcome: {outcome}",
            f"Proposal Score: {obj.proposal_score}",
            f"Document Scores: {scores_pretty}",
            f"Missing Documents: {missing}",
            f"Failed Documents: {failed}",
            f"Final Score: {final_score}   Rank: {rank}",
            "",
            f"Notes: {obj.notes or '—'}",
        ]
        return "\n".join(lines) + eval_block
