# compliance/management/commands/process_tender.py
from django.core.management.base import BaseCommand
from tenders.models import Tender
from bids.models import Bid
from ai.compliance.engine import run_compliance_check, rank_bids_for_tender
from notifications.utils import notify_user

class Command(BaseCommand):
    help = "Process all bids under a tender: verify documents, score proposals, and rank bids"

    def add_arguments(self, parser):
        parser.add_argument("tender_id", type=int)

    def handle(self, *args, **options):
        tender_id = options["tender_id"]

        try:
            tender = Tender.objects.get(pk=tender_id)
        except Tender.DoesNotExist:
            self.stdout.write(self.style.ERROR("Tender not found"))
            return

        bids = Bid.objects.filter(tender=tender)

        if not bids.exists():
            self.stdout.write("No bids submitted yet.")
            return

        for bid in bids:
            self.stdout.write(f"🔍 Verifying Bid #{bid.id}...")
            compliance = run_compliance_check(bid)

            status = "COMPLIANT" if compliance.is_compliant else "NOT COMPLIANT"
            self.stdout.write(self.style.SUCCESS(f"✅ Bid #{bid.id} → {status}"))

            # Add detailed report
            self.stdout.write("   📄 Missing Docs: " + ", ".join(compliance.missing_documents or []))
            self.stdout.write("   ❌ Failed Docs: " + ", ".join(compliance.failed_documents or []))
            self.stdout.write("   📊 Document Scores:")

            for doc_type, score in (compliance.document_scores or {}).items():
                self.stdout.write(f"      - {doc_type}: {score}")
            
            self.stdout.write(f"   📝 Proposal Score: {compliance.proposal_score}")
            self.stdout.write(f"   📝 Evaluation: {compliance.evaluation}")
            rank_bids_for_tender(tender_id)
            self.stdout.write(self.style.SUCCESS("🏆 Bids ranked by score."))

            notify_user(
                recipient=bid.submitted_by,
                message=f"Your bid for '{tender.title}' was processed — result: {'✅ Compliant' if compliance.is_compliant else '❌ Not Compliant'}",
                data={"type": "bid_processed", "bid_id": bid.id}
            )



