from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from wagtail_modeladmin.helpers import AdminURLHelper
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404


from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.response import Response
from rest_framework import status
from curator.auth import APIKeyAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, authentication_classes, renderer_classes
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from .serializers import (
    MinimalCodebaseSerializer,
    MinimalEventSerializer,
    MinimalJobSerializer,
    SpamModerationSerializer,
    SpamUpdateSerializer,
)
from curator.models import TagCleanup
from curator.wagtail_hooks import TagCleanupAction

from core.models import SpamModeration

import bleach

TAG_CLEANUP_ACTIONS = {
    TagCleanupAction.process.name: TagCleanup.objects.process,
    TagCleanupAction.find_by_porter_stemmer.name: lambda: TagCleanup.objects.bulk_create(
        TagCleanup.find_groups_by_porter_stemmer()
    ),
    TagCleanupAction.find_by_platform_and_language.name: lambda: TagCleanup.objects.bulk_create(
        TagCleanup.find_groups_by_platform_and_language()
    ),
    TagCleanupAction.delete_all_active.name: lambda: TagCleanup.objects.filter(
        transaction_id__isnull=True
    ).delete(),
}


@require_POST
@permission_required("curator.process_tagcleanup", raise_exception=True)
def process_pending_tag_cleanups(request):
    action_name = request.POST["action"]
    action = TAG_CLEANUP_ACTIONS.get(action_name)
    if not action:
        return HttpResponseBadRequest(f"invalid action: {bleach.clean(action_name)}")
    action()
    return HttpResponseRedirect(AdminURLHelper(TagCleanup).index_url)


def confirm_spam_view(request, instance_id):
    spam_moderation = get_object_or_404(SpamModeration, id=instance_id)
    deactivate_user = request.GET.get("deactivate_user") == "true"
    if deactivate_user:
        user = spam_moderation.content_object.submitter
        user.is_active = False
        user.save()
        messages.success(
            request, f"Content confirmed as spam and user: {user} deactivated."
        )
    spam_moderation.status = SpamModeration.Status.SPAM
    spam_moderation.reviewer = request.user
    spam_moderation.save()
    messages.success(request, "Content confirmed as spam.")
    return HttpResponseRedirect(AdminURLHelper(SpamModeration).index_url)


def reject_spam_view(request, instance_id):
    spam_moderation = get_object_or_404(SpamModeration, id=instance_id)
    spam_moderation.status = SpamModeration.Status.NOT_SPAM
    spam_moderation.reviewer = request.user
    spam_moderation.save()
    messages.success(request, "Content marked as not spam.")
    return HttpResponseRedirect(AdminURLHelper(SpamModeration).index_url)


@api_view(["GET"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([AllowAny])
@renderer_classes([CamelCaseJSONRenderer])
def get_latest_spam_batch(request):

    # Get SpamModeration records with status SCHEDULED_FOR_CHECK
    latest_spam_batch = (
        SpamModeration.objects.filter(status=SpamModeration.Status.SCHEDULED_FOR_CHECK)
        .select_related("content_type")
        .prefetch_related("content_object")[:100]
    )

    # Serialize the data needed for the spam check
    serialized_data = []
    for spam_moderation in latest_spam_batch:
        content_object = spam_moderation.content_object
        content_type = spam_moderation.content_type.model

        if content_type == "job":
            content_serializer = MinimalJobSerializer(content_object)
        elif content_type == "event":
            content_serializer = MinimalEventSerializer(content_object)
        elif content_type == "codebase":
            content_serializer = MinimalCodebaseSerializer(content_object)
        else:
            continue

        spam_content_to_check = SpamModerationSerializer(spam_moderation).data
        spam_content_to_check["content_object"] = content_serializer.data

        serialized_data.append(spam_content_to_check)

    return Response(serialized_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([AllowAny])
@renderer_classes([CamelCaseJSONRenderer])
def update_spam_moderation(request):
    serializer = SpamUpdateSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        print(data)
        print(data["object_id"])
        try:
            spam_moderation = SpamModeration.objects.get(
                id=data["object_id"],
            )
        except ObjectDoesNotExist:
            return Response(
                {"error": "SpamModeration object not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update SpamModeration object
        spam_moderation.status = (
            SpamModeration.Status.SPAM_LIKELY
            if data["is_spam"]
            else SpamModeration.Status.NOT_SPAM_LIKELY
        )
        spam_moderation.detection_method = "LLM"

        current_details = (
            spam_moderation.detection_details
            if spam_moderation.detection_details
            else {}
        )
        new_details = {
            "spam_indicators": data.get("spam_indicators", []),
            "reasoning": data.get("reasoning", ""),
            "confidence": data.get("confidence", None),
        }
        current_details.update(new_details)
        spam_moderation.detection_details = current_details

        spam_moderation.save()

        # Update the related content object
        content_object = spam_moderation.content_object
        if hasattr(content_object, "is_marked_spam"):
            content_object.is_marked_spam = data["is_spam"]
            content_object.save()

        return Response(
            {"message": "SpamModeration updated successfully"},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
