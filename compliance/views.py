from rest_framework import viewsets, permissions
from .models import ComplianceCheck
from .serializers import ComplianceCheckSerializer

class ComplianceCheckViewSet(viewsets.ModelViewSet):
    queryset = ComplianceCheck.objects.all()
    serializer_class = ComplianceCheckSerializer
    permission_classes = [permissions.IsAuthenticated]
