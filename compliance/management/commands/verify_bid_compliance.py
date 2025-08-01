# compliance/management/commands/verify_bid_compliance.py
from django.core.management.base import BaseCommand
from tenders.models import Tender
from bids.models import Bid
from ai.compliance.engine import run_compliance_check


class Command(BaseCommand):
    help = "Run compliance verification for all bids under a tender"

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
