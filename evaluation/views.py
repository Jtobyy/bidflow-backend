from rest_framework import viewsets, permissions
from .models import Evaluation
from .serializers import EvaluationSerializer
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework import permissions
from ai.services.ocr_service import extract_text_from_image
from ai.services.compliance_service import check_compliance
from ai.services.scoring_service import score_bid
import tempfile
from rest_framework.parsers import MultiPartParser, FormParser
from PIL import Image
from bids.models import Bid

class EvaluationViewSet(viewsets.ModelViewSet):
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def evaluate_bid(request):
    """
    AI-powered bid evaluation: OCR → Compliance → Scoring
    Accepts either:
    - Direct file uploads via 'documents' (multipart/form-data)
    - A 'bid_id' referencing an existing Bid with a document
    """

    bid_id = request.data.get('bid_id')
    files = request.FILES.getlist('documents')

    if not bid_id and not files:
        return Response({"error": "Provide either 'bid_id' or upload 'documents'."}, status=400)

    all_text = ""

    # If evaluating based on bid_id
    if bid_id:
        try:
            bid = Bid.objects.get(id=bid_id)
            if not bid.document:
                return Response({"error": "This bid has no document attached."}, status=400)

            with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                for chunk in bid.document.chunks():
                    temp_file.write(chunk)
                temp_file.flush()

                img = Image.open(temp_file.name)
                text = extract_text_from_image(temp_file.name)
                all_text += text + "\n"

        except Bid.DoesNotExist:
            return Response({"error": "Bid not found."}, status=404)
        except Exception as e:
            return Response({"error": f"Error processing bid document: {str(e)}"}, status=500)

    # If evaluating based on direct file uploads
    elif files:
        for uploaded_file in files:
            with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()

                try:
                    img = Image.open(temp_file.name)
                    text = extract_text_from_image(temp_file.name)
                    all_text += text + "\n"
                except Exception as e:
                    all_text += "Error processing this file.\n"
                    print(f"OCR error: {e}")

    # AI Compliance & Scoring
    compliance_result = check_compliance(all_text)
    scoring_result = score_bid(all_text)

    # If evaluated from bid, save Evaluation instance
    if bid_id:
        Evaluation.objects.create(
            bid=bid,
            evaluator=request.user,
            method='QCBS',
            technical_score=scoring_result['score'],  # or map appropriately
            total_score=scoring_result['score'],      # optional, or calculate
            comments=f"Compliance: {compliance_result} | Score: {scoring_result}"
        )


    return Response({
        "text_preview": all_text[:300] + "...",
        "compliance": compliance_result,
        "score": scoring_result
    })