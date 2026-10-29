"""
Wagtail admin pages for reviewing spam detection results and moderating flagged content
"""

import json

from core.models import ComsesGroups, Event, Job, MemberProfile, SpamDetectionSettings, SpamModeration, User
from core.spam import PROVIDERS
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from library.models import Codebase

TABS = {
    "all": ("All", None),
    "spam": ("Spam", {"status": SpamModeration.Status.SPAM}),
    "not_spam": ("Not spam", {"status": SpamModeration.Status.NOT_SPAM}),
    "reviewed": ("Reviewed", {"reviewer__isnull": False}),
}

SORTS = {
    "recent": "Most recent",
    "uncertain": "Least certain",
}

CONTENT_TYPES = {
    "job": ("Jobs", Job),
    "event": ("Events", Event),
    "codebase": ("Models", Codebase),
    "profile": ("Profiles", MemberProfile),
    "user": ("Accounts", User),
}


def is_moderator(user) -> bool:
    return user.is_superuser or ComsesGroups.is_moderator(user)


def moderator_required(view):
    def wrapped(request, *args, **kwargs):
        if not is_moderator(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def describe(moderation: SpamModeration) -> dict:
    """
    Display details for the moderated object, which may have been deleted
    """
    content = moderation.content_object
    if content is None:
        return {"title": "Deleted content", "kind": moderation.content_type.name, "url": None}
    if isinstance(content, User):
        title, url = content.username, reverse("core:profile-detail", kwargs={"pk": content.id})
    elif isinstance(content, MemberProfile):
        title, url = content.name, content.get_absolute_url()
    else:
        title, url = content.title, content.get_absolute_url()
    return {"title": title, "kind": content._meta.verbose_name, "url": url}


def config_context() -> dict:
    config = SpamDetectionSettings.load()
    providers = dict(SpamDetectionSettings.Provider.choices)
    slots = [
        ("Primary", config.primary_provider, config.primary_model, config.primary_threshold),
        ("Fallback", config.fallback_provider, config.fallback_model, config.fallback_threshold),
    ]
    return {
        "config": config,
        "config_url": reverse("wagtailsettings:edit", args=["core", "spamdetectionsettings"]),
        "models": [
            {
                "role": role,
                "provider": providers[provider],
                "model": model,
                "threshold": threshold,
                "has_api_key": PROVIDERS[provider].is_configured(),
            }
            for role, provider, model, threshold in slots
            if provider and model
        ],
    }


def input_sections(model_input: dict) -> list:
    """
    Group what the model saw into labelled sections: the submission itself, then nested context like the submitter
    """

    def label(key):
        return key.replace("_", " ").capitalize()

    def display(value):
        return ", ".join(map(str, value)) if isinstance(value, list) else value

    top = {key: value for key, value in model_input.items() if not isinstance(value, dict) and key != "type"}
    nested = [(label(key), value) for key, value in model_input.items() if isinstance(value, dict)]
    sections = [(label(model_input.get("type", "submission")), top), *nested]
    return [(title, [(label(key), display(value)) for key, value in fields.items()]) for title, fields in sections]


@moderator_required
def index(request):
    tab = request.GET.get("tab") if request.GET.get("tab") in TABS else "spam"
    sort = request.GET.get("sort") if request.GET.get("sort") in SORTS else "recent"
    kind = request.GET.get("type", "")
    moderations = SpamModeration.objects.select_related("reviewer")
    if sort == "uncertain":
        moderations = moderations.filter(reviewer__isnull=True).least_certain()
    else:
        moderations = moderations.order_by("-last_modified")
    if TABS[tab][1]:
        moderations = moderations.filter(**TABS[tab][1])
    if kind in CONTENT_TYPES:
        moderations = moderations.filter(content_type=ContentType.objects.get_for_model(CONTENT_TYPES[kind][1]))
    page = Paginator(moderations.prefetch_related("content_object"), 30).get_page(request.GET.get("page"))
    return TemplateResponse(
        request,
        "curator/spam/index.html",
        {
            **config_context(),
            "page": page,
            "rows": [(moderation, describe(moderation)) for moderation in page],
            "tab": tab,
            "sort": sort,
            "kind": kind,
            "tabs": [(key, label) for key, (label, _) in TABS.items()],
            "sorts": SORTS.items(),
            "kinds": [(key, label) for key, (label, _) in CONTENT_TYPES.items()],
        },
    )


@moderator_required
def detail(request, pk):
    moderation = get_object_or_404(SpamModeration, pk=pk)
    model_input = moderation.detection_details.get("input")
    return TemplateResponse(
        request,
        "curator/spam/detail.html",
        {
            **config_context(),
            "moderation": moderation,
            "content": describe(moderation),
            "submitter": moderation.submitter,
            "input_sections": input_sections(model_input) if model_input else [],
            "raw_details": json.dumps(moderation.detection_details, indent=2, ensure_ascii=False),
            # anything else a detection method recorded, e.g. on legacy honeypot records
            "other_details": {
                key: value
                for key, value in moderation.detection_details.items()
                if key not in {"input", "spam_probability", "threshold", "latency_ms", "fallback_from"}
            },
        },
    )


@require_POST
@moderator_required
@transaction.atomic
def review(request, pk):
    moderation = get_object_or_404(SpamModeration, pk=pk)
    decision = request.POST.get("decision")
    if decision not in {"spam", "not_spam", "spam_deactivate"}:
        messages.error(request, "Unknown review decision.")
        return redirect("curator_spam:detail", pk=pk)
    content = moderation.content_object
    if content is not None:
        type(content).objects.select_for_update().get(pk=content.pk)
        moderation.refresh_from_db()
    moderation.review(request.user, is_spam=decision != "not_spam", notes=request.POST.get("notes", "").strip())
    title = describe(moderation)["title"]
    if decision == "spam_deactivate":
        user = moderation.submitter
        if user is None or user.is_superuser:
            messages.error(request, f"Marked “{title}” as spam, but its submitter can't be deactivated.")
        else:
            user.is_active = False
            user.save()
            messages.success(request, f"Marked “{title}” as spam and deactivated {user.username}.")
    else:
        label = "spam" if decision == "spam" else "not spam"
        messages.success(request, f"Marked “{title}” as {label}.")
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("curator_spam:index")


urlpatterns = [
    path("", index, name="index"),
    path("<int:pk>/", detail, name="detail"),
    path("<int:pk>/review/", review, name="review"),
]
