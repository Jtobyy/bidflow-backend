from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BidViewSet, BidDocumentViewSet

router = DefaultRouter()
router.register(r'bids', BidViewSet)
router.register(r'bids-documents', BidDocumentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
