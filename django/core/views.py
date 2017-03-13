from rest_framework.decorators import api_view, permission_classes
from . import summarization
from rest_framework.response import Response


@api_view(['POST'], exclude_from_schema=True)
@permission_classes([])
def summarize_text(request):
    return Response(summarization.summarize_to_text(request.data['description'], 2))