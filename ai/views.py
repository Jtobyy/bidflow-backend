from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q
from django.utils.timezone import now, timedelta

from tenders.models import Tender
from bids.models import Bid, BidDocument
from users.models import User

class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Summary
        tenders = Tender.objects.count()
        bids = Bid.objects.count()
        documents = BidDocument.objects.count()
        users = User.objects.count()
        compliant_bids = Bid.objects.filter(compliance__is_compliant=True).count()
        pending_reviews = Bid.objects.filter(status="pending").count()

        # 2. Leaderboard
        leaderboard = (
            Bid.objects.values(
                'submitted_by__username',
                'submitted_by__company__name'  # Assumes FK: User.company
            )
            .annotate(
                avg_score=Avg('score'),
                bids=Count('id'),
                compliant=Count('compliance__is_compliant', filter=Q(compliance__is_compliant=True)),
            )
            .order_by('-avg_score')[:3]
        )

        leaderboard_data = [
            {
                "company": row["submitted_by__company__name"] or row["submitted_by__username"],
                "avg_score": int(row["avg_score"]) if row["avg_score"] else 0,
                "bids": row["bids"],
                "compliance": f"{int(100 * row['compliant'] / row['bids']) if row['bids'] else 0}%",
            }
            for row in leaderboard
        ]

        # 3. Bid Evaluation Status Chart (last 6 months)
        months = []
        bid_eval_chart = []
        today = now()
        for i in reversed(range(6)):
            dt = (today.replace(day=1) - timedelta(days=30*i))
            month_label = dt.strftime("%b")
            qs = Bid.objects.filter(submitted_at__month=dt.month)
            fully = qs.filter(status__in=['accepted', 'reviewed'], score__isnull=False).count()
            partial = qs.filter(status='reviewed', score__isnull=True).count()
            rejected = qs.filter(status__in=['rejected', 'disqualified']).count()
            pending = qs.filter(status='pending').count()
            bid_eval_chart.append({
                "month": month_label,
                "Fully": fully,
                "Partial": partial,
                "Rejected": rejected,
                "Pending": pending,
            })

        # 4. Recent Activity
        recent_activity = []
        latest_bids = Bid.objects.order_by('-submitted_at')[:8]
        for bid in latest_bids:
            if getattr(bid, "compliance", None) and bid.compliance.is_compliant:
                recent_activity.append({
                    "type": "compliance_passed",
                    "desc": f"Bid from {bid.submitted_by.username} passed compliance."
                })
            elif bid.status == "pending":
                recent_activity.append({
                    "type": "pending_review",
                    "desc": f"Bid by {bid.submitted_by.username} is pending review."
                })
            elif bid.status == "rejected":
                recent_activity.append({
                    "type": "rejected",
                    "desc": f"Bid by {bid.submitted_by.username} was rejected."
                })
            else:
                recent_activity.append({
                    "type": "bid_submitted",
                    "desc": f"Bid submitted for Tender {bid.tender.id}."
                })

        # 5. Alerts & Suggestions
        one_week_ago = now() - timedelta(days=7)
        failed_this_week = Bid.objects.filter(
            compliance__is_compliant=False,
            submitted_at__gte=one_week_ago
        ).count()
        alerts = []
        if failed_this_week:
            alerts.append({"type": "warning", "text": f"{failed_this_week} bids failed compliance checks this week."})

        return Response({
            "tenders": tenders,
            "bids": bids,
            "documents": documents,
            "users": users,
            "compliant_bids": compliant_bids,
            "pending_reviews": pending_reviews,
            "leaderboard": leaderboard_data,
            "recent_activity": recent_activity,
            "alerts": alerts,
            "bid_evaluation_chart": bid_eval_chart,
        })
