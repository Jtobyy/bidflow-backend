from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import TenderViewSet, tender_summary_excel

router = DefaultRouter()
router.register(r'tenders', TenderViewSet)

urlpatterns = router.urls + [
    path('tender-summary-report/', tender_summary_excel, name='tender-summary-report'),
]
