from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EvaluationViewSet, evaluate_bid

router = DefaultRouter()
router.register(r'evaluations', EvaluationViewSet)

urlpatterns = [
    path('evaluations/automated/', evaluate_bid),
    path('', include(router.urls)),
]
