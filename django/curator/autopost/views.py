from django.http import JsonResponse
from .autopost import autopost_to_bluesky

def autopost_view(request):
    try:
        text = "This is an autopost"
        response = autopost_to_bluesky(text)
        return JsonResponse({"success": True, "data": response})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
