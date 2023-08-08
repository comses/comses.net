import logging
import json

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import QueryDict
from django.template.loader import get_template
from django.views.generic import TemplateView, CreateView
from django.views.generic.list import ListView
from rest_framework import generics

from core.utils import send_markdown_email
from core.pagination import SmallResultSetPagination
from .forms import ConferenceSubmissionForm
from .metrics import Metrics
from .models import (
    ComsesDigest,
    FeaturedContentItem,
    ContactPage,
    ConferencePage,
)
from .serializers import (
    FeaturedContentItemSerializer,
)
from .search import GeneralSearch


logger = logging.getLogger(__name__)

"""
Contains wagtail related views
"""


class ContactSentView(TemplateView):
    template_name = "home/about/contact-sent.jinja"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["page"] = ContactPage.objects.first()
        return context_data


class FeaturedContentListAPIView(generics.ListAPIView):
    serializer_class = FeaturedContentItemSerializer
    queryset = FeaturedContentItem.objects.all()
    pagination_class = SmallResultSetPagination


class MetricsView(TemplateView):
    template_name = "home/about/metrics.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        m = Metrics()
        metrics_data_json = json.dumps(m.get_all_data())
        context["metrics_data_json"] = metrics_data_json
        return context


class SearchView(TemplateView):
    template_name = "home/search.jinja"

    def get_context_data(self, **kwargs):
        search = GeneralSearch()
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get("query")
        page = self.request.GET.get("page", 1)
        try:
            page = int(page)
        except ValueError:
            page = 1
        if query is not None:
            results, total = search.search(query, start=(page - 1) * 10)
        else:
            results, total = [], 0

        pagination_context = SmallResultSetPagination.create_paginated_context_data(
            query=query,
            data=results,
            current_page_number=page,
            count=total,
            query_params=QueryDict(query_string="query={}".format(query)),
        )
        context["__all__"] = pagination_context
        context.update(pagination_context)
        return context


class DigestView(ListView):
    template_name = "home/digest.jinja"
    model = ComsesDigest
    context_object_name = "digests"


class ConferenceSubmissionView(LoginRequiredMixin, CreateView):
    template_name = "home/conference/submission.jinja"
    form_class = ConferenceSubmissionForm

    @property
    def conference(self):
        if getattr(self, "_conference", None) is None:
            self._conference = ConferencePage.objects.get(slug=self.kwargs["slug"])
        return self._conference

    def get_success_url(self):
        return self.conference.url

    @property
    def submitter(self):
        return self.request.user.member_profile

    def conference_requirements(self):
        # returns a list of tuples of id/description
        return [
            ("videoLength", "The length of my submitted video is under 12 minutes."),
            # ('presentationLanguage', 'My presentation is in English.'),
            (
                "presentationTheme",
                "My presentation is related to the theme of this conference.",
            ),
            ("fullMemberProfile", "I have a current member profile page."),
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["conference"] = self.conference
        ctx["submitter"] = self.submitter
        ctx["conference_requirements"] = self.conference_requirements()
        return ctx

    def form_valid(self, form):
        form.instance.submitter = self.submitter
        form.instance.conference = self.conference
        # send an email to editors
        self._send_email(
            form, submitter=form.instance.submitter, conference=form.instance.conference
        )
        return super().form_valid(form)

    def _send_email(self, form, submitter=None, conference=None):
        template = get_template("home/conference/email/notify.jinja")
        markdown_content = template.render(
            context={
                "form": form,
                "conference": conference,
                "submitter": submitter,
                "profile_url": self.request.build_absolute_uri(submitter.profile_url),
            }
        )
        send_markdown_email(
            subject="{0} presentation submission".format(conference.title),
            body=markdown_content,
            to=[submitter.email],
            bcc=[settings.SERVER_EMAIL],
        )

    def form_invalid(self, form):
        logger.debug("form was invalid: %s", form)
        response = super().form_invalid(form)
        logger.debug("invalid form response: %s", response)
        return response
