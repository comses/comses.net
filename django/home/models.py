import logging
from datetime import date, datetime
from textwrap import shorten

import requests
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from wagtail.admin.panels import (
    FieldPanel,
    InlinePanel,
    PageChooserPanel,
    MultiFieldPanel,
)
from wagtail import blocks
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, Orderable
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from core.discourse import build_discourse_url
from core.fields import MarkdownField, TutorialMarkdownField
from core.fs import get_canonical_image
from core.models import MemberProfile, Platform, Event, Job

# FIXME: should these models be pushed into core..
from library.models import Codebase, CodebaseRelease, Contributor

logger = logging.getLogger(__name__)

"""
Wagtail Page models and related supporting Models and Settings

"""


class UserMessage(models.Model):
    """
    FIXME: consider removing this class, use email for messaging.
    """

    user = models.ForeignKey(User, related_name="inbox", on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name="outbox", on_delete=models.CASCADE)
    message = models.CharField(max_length=512)
    date_created = models.DateTimeField(auto_now_add=True)
    read_on = models.DateTimeField(null=True, blank=True)

    def is_read(self):
        return self.read_on is not None


class LinkFields(models.Model):
    """
    Cribbed from github.com/wagtail/wagtaildemo
    """

    link_external = models.URLField("External link", blank=True)
    link_page = models.ForeignKey(
        Page, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    link_codebase = models.ForeignKey(
        "library.Codebase",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )

    @property
    def link(self):
        if self.link_page:
            return self.link_page.url
        elif self.link_codebase:
            return self.link_codebase.get_absolute_url()
        else:
            return self.link_external

    panels = [
        FieldPanel("link_external"),
        PageChooserPanel("link_page"),
        # figure out how to manually link codebase / events / jobs into FeaturedContentItem
        # CodebaseChooserPanel('link_codebase'),
    ]

    class Meta:
        abstract = True


class CarouselItem(LinkFields):
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    codebase_image = models.ForeignKey(
        "library.CodebaseImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    embed_url = models.URLField("Embed URL", blank=True)
    caption = models.CharField(max_length=255)
    summary = models.TextField(max_length=600, blank=True)
    title = models.CharField(max_length=255)
    panels = [
        FieldPanel("image"),
        FieldPanel("codebase_image"),
        FieldPanel("embed_url"),
        FieldPanel("caption"),
        FieldPanel("title"),
        MultiFieldPanel(LinkFields.panels, "Link"),
    ]

    @property
    def featured_image(self):
        if self.image:
            return self.image
        elif self.codebase_image:
            return self.codebase_image
        return None

    class Meta:
        abstract = True


class FeaturedContentItem(Orderable, CarouselItem):
    page = ParentalKey("home.LandingPage", related_name="featured_content_queue")


class LandingPage(Page):
    template = "home/index.jinja"
    FEATURED_CONTENT_COUNT = 6
    MAX_CALLOUT_ENTRIES = 3
    RECENT_FORUM_ACTIVITY_COUNT = 5

    mission_statement = models.CharField(max_length=512)
    community_statement = models.TextField()

    def get_featured_content(self):
        return self.featured_content_queue.select_related(
            "image", "codebase_image", "link_codebase", "link_page"
        ).all()[: self.FEATURED_CONTENT_COUNT]

    def get_canned_forum_activity(self):
        random_submitters = User.objects.select_related("member_profile").filter(
            pk__in=(3, 5, 7, 11, 13, 17)
        )
        return [
            {
                "title": "Generated Forum Topic {}".format(i),
                "submitter_name": random_submitters[i].member_profile.name,
                "submitter_url": random_submitters[i].member_profile.get_absolute_url(),
                "date_created": datetime.now(),
                "url": "https://forum.example.com/topic/{}".format(i),
            }
            for i in range(self.RECENT_FORUM_ACTIVITY_COUNT)
        ]

    def _discourse_username_to_submitter(self, username, topic, topic_title):
        submitter = None
        submitter_url = None
        if username != "comses":
            try:
                submitter = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        if submitter is None:
            category_id = topic["category_id"]
            logger.debug(
                "category id: %s, topic title: %s, topic: %s",
                category_id,
                topic_title,
                topic,
            )
            # special case lookup for real submitter
            # FIXME: get rid of magic constants
            target_object = None
            if category_id == 6:
                # jobs and appointments
                target_object = (
                    Job.objects.filter(title=topic_title)
                    .order_by("-date_created")
                    .first()
                )
            elif category_id == 7:
                # events
                target_object = (
                    Event.objects.filter(title=topic_title)
                    .order_by("-date_created")
                    .first()
                )
            elif category_id == 8:
                target_object = (
                    Codebase.objects.filter(title=topic_title)
                    .order_by("-date_created")
                    .first()
                )
            if target_object:
                submitter = target_object.submitter
                submitter_url = submitter.member_profile.get_absolute_url()
            else:
                submitter = User.get_anonymous()
        return submitter, submitter_url

    def get_recent_forum_activity(self):
        # FIXME: refactor and clean up logic to form a more sensible discourse api
        # Discourse API endpoint documented at http://docs.discourse.org/#tag/Topics%2Fpaths%2F~1latest.json%2Fget
        if settings.DEPLOY_ENVIRONMENT.is_development:
            return self.get_canned_forum_activity()
        recent_forum_activity = cache.get("recent_forum_activity")
        if recent_forum_activity:
            return recent_forum_activity
        # transform topics list of dictionaries into web template format with title, submitter, date_created, and url.
        try:
            r = requests.get(
                build_discourse_url("latest.json"),
                params={"order": "created", "sort": "asc"},
                timeout=3.0,
            )
            posts_dict = r.json()
            topics = posts_dict["topic_list"]["topics"]
            recent_forum_activity = []
            for topic in topics[: self.RECENT_FORUM_ACTIVITY_COUNT]:
                topic_title = topic["title"]
                topic_url = build_discourse_url(
                    "t/{0}/{1}".format(topic["slug"], topic["id"])
                )
                # getting back to the original submitter involves some trickery.
                # The Discourse embed Javascript queues up a crawler to hit the given page and parses it for content to use
                # as the initial topic text. However, this topic gets added as a specific Discourse User (`comses`,
                # see https://meta.discourse.org/t/embedding-discourse-comments-via-javascript/31963/150 for more details)
                # and so we won't always have the direct username of the submitter without looking it up by
                # 1. Discourse category_id (6 = jobs & appointments, 7 = events, 8 = codebase)
                # 2. Title (not guaranteed to be unique)

                last_poster_username = topic["last_poster_username"]
                submitter, submitter_url = self._discourse_username_to_submitter(
                    last_poster_username, topic, topic_title
                )

                recent_forum_activity.append(
                    {
                        "title": topic_title,
                        "submitter_name": submitter.username,
                        "submitter_url": submitter_url,
                        # FIXME: handle created_at=None gracefully, via default date?
                        "date_created": datetime.strptime(
                            topic.get("created_at"), "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "url": topic_url,
                    }
                )
            cache.set("recent_forum_activity", recent_forum_activity, 3600)
            return recent_forum_activity
        except Exception as e:
            logger.exception(e)
            return []

    def get_latest_jobs(self):
        return Job.objects.order_by("-date_created")[: self.MAX_CALLOUT_ENTRIES]

    def get_upcoming_events(self):
        return Event.objects.upcoming().order_by("start_date")[
            : self.MAX_CALLOUT_ENTRIES
        ]

    def get_sitemap_urls(self, request):
        sitemap_urls = super().get_sitemap_urls(request)
        # manually add list index urls to the existing sitemap
        codebases_url = request.build_absolute_uri("/codebases/")
        jobs_url = request.build_absolute_uri("/jobs/")
        events_url = request.build_absolute_uri("/events/")
        digest_url = request.build_absolute_uri("/digest/")
        sitemap_urls.extend(
            [
                {
                    "location": codebases_url,
                    "lastmod": CodebaseRelease.objects.public().last().last_modified,
                },
                {"location": jobs_url, "lastmod": Job.objects.last().last_modified},
                {"location": events_url, "lastmod": Event.objects.last().last_modified},
                {"location": digest_url},
            ]
        )
        return sitemap_urls

    def get_context(self, request, *args, **kwargs):
        context = super(LandingPage, self).get_context(request, *args, **kwargs)
        context["featured_content"] = self.get_featured_content()
        context["recent_forum_activity"] = self.get_recent_forum_activity()
        context["latest_jobs"] = self.get_latest_jobs()
        context["upcoming_events"] = self.get_upcoming_events()
        return context

    content_panels = Page.content_panels + [
        FieldPanel("mission_statement", widget=forms.Textarea),
        FieldPanel("community_statement"),
        InlinePanel("featured_content_queue", label=_("Featured Content")),
    ]


class CategoryIndexItem(Orderable, models.Model):
    page = ParentalKey("home.CategoryIndexPage", related_name="callouts")
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    url = models.CharField(
        "Relative path, absolute path, or URL", max_length=200, blank=True
    )
    title = models.CharField(max_length=255)
    caption = models.CharField(max_length=600)

    def __str__(self):
        return "{0} {1}".format(self.title, self.url)


class SubnavigationMenu:
    pass


class SubNavigationLink(Orderable, models.Model):
    page = ParentalKey(Page, related_name="navigation_links")
    url = models.CharField("Relative path, absolute path, or full URL", max_length=255)
    title = models.CharField(max_length=128)

    def __str__(self):
        return f"SubNavigationLink for page {self.page}: {self.title} ({self.url})"


class Breadcrumb(Orderable, models.Model):
    page = ParentalKey(Page, related_name="breadcrumbs")
    url = models.CharField(
        "Relative / absolute path or full URL", max_length=255, blank=True
    )
    title = models.CharField(max_length=255)

    def __str__(self):
        return f"Breadcrumb for page {self.page}: {self.title} ({self.url})"


class NavigationMixin(object):
    def add_breadcrumbs(self, breadcrumb_tuples):
        self._add_tuples(breadcrumb_tuples, Breadcrumb)

    def get_breadcrumbs(self):
        return [
            {"url": item.url, "text": item.title} for item in self.breadcrumbs.all()
        ]

    def _add_tuples(self, tuples, cls):
        related_name = cls._meta.get_field("page").related_query_name()
        related_manager = getattr(self, related_name)
        for idx, (title, url) in enumerate(tuples):
            related_manager.add(cls(title=title, url=url, sort_order=idx))

    def replace_navigation_links(self, navigation_tuples):
        self.navigation_links.all().delete()
        self.add_navigation_links(navigation_tuples)

    def add_navigation_links(self, navigation_tuples):
        """
        Takes an ordered list of tuples and adds them as navigation links.
        :param navigation_tuples:
        :return:
        """
        self._add_tuples(navigation_tuples, SubNavigationLink)

    def get_navigation_links(self):
        """
        Returns a nested dict for use by the subnav Jinja2 tag.
        :return:
        """
        return [
            {
                "url": nav.url,
                "text": nav.title,
                "active": nav.url.endswith(self.slug + "/"),
            }
            for nav in self.navigation_links.all()
        ]


class CategoryIndexPage(NavigationMixin, Page):
    template = models.CharField(max_length=256, default="home/category_index.jinja")
    heading = models.CharField(
        max_length=256, help_text=_("Short name to be placed in introduction header.")
    )
    summary = models.CharField(
        max_length=5000, help_text=_("Summary blurb for this category index page.")
    )

    def add_callout(
        self, image_path, title, caption, sort_order=None, user=None, url=""
    ):
        if user is None:
            user = User.objects.get(username="alee")
        _image = get_canonical_image(title=title, path=image_path, user=user)
        self.callouts.add(
            CategoryIndexItem(
                title=title,
                sort_order=sort_order,
                caption=caption,
                image=_image,
                url=url,
            )
        )

    content_panels = Page.content_panels + [
        # don't expose template to web form for now, could wreak havoc
        FieldPanel("heading"),
        FieldPanel("template"),
        FieldPanel("summary", widget=forms.Textarea),
        InlinePanel("callouts", label=_("Captioned Image Callouts")),
        InlinePanel("navigation_links", label=_("Subnavigation Links")),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("summary", partial_match=True)
    ]


class EducationPage(NavigationMixin, Page):
    """Education page that indexes external or internal links to tutorial pages"""

    template = models.CharField(max_length=256, default="home/education.jinja")
    heading = models.CharField(
        max_length=256, help_text=_("Short name to be placed in introduction header.")
    )
    summary = models.CharField(
        max_length=5000, help_text=_("Markdown-enabled summary blurb for this page.")
    )

    def add_card(
        self, image_path, title, summary, tags=None, sort_order=None, user=None, url=""
    ):
        if self.cards.filter(title=title):
            return
        if user is None:
            user = User.objects.get(username="alee")
        _image = (
            get_canonical_image(title=title, path=image_path, user=user)
            if image_path
            else None
        )
        card = TutorialCard(
            title=title,
            sort_order=sort_order,
            summary=summary,
            thumbnail_image=_image,
            url=url,
        )
        for tag in tags:
            card.tags.add(tag)
        self.cards.add(card)

    content_panels = Page.content_panels + [
        FieldPanel("heading"),
        FieldPanel("summary", widget=forms.Textarea),
        InlinePanel("cards", label=_("Tutorial Cards")),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        cards = TutorialCard.objects.all()
        tag = request.GET.get("tag")
        if tag:
            cards = cards.filter(tags__name=tag)
            context["cards"] = cards.filter(tags__name=tag)
        context["cards"] = cards
        return context


class TutorialTag(TaggedItemBase):
    content_object = ParentalKey("TutorialCard", related_name="tagged_items")


class TutorialCard(Orderable, ClusterableModel):
    """Cards displayed in the Education Page"""

    page = ParentalKey("home.EducationPage", related_name="cards")
    url = models.CharField("Relative path, absolute path, or URL", max_length=200)
    title = models.CharField(max_length=256)
    summary = models.CharField(
        max_length=1000,
        help_text=_("Markdown-enabled summary for this tutorial card"),
        blank=True,
    )
    thumbnail_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    tags = ClusterTaggableManager(through=TutorialTag, blank=True)

    panels = [
        FieldPanel("url"),
        FieldPanel("title"),
        FieldPanel("summary", widget=forms.Textarea),
        FieldPanel("thumbnail_image"),
        FieldPanel("tags"),
    ]

    def __str__(self):
        return "{0} {1}".format(self.title, self.url)


class TutorialDetailPage(NavigationMixin, Page):
    """Tutorial page that contains a body formatted with markdown"""

    heading = models.CharField(
        max_length=128,
        blank=True,
        help_text=_(
            "Large heading text placed on the blue background introduction header"
        ),
    )
    template = models.CharField(max_length=128, default="home/tutorial.jinja")
    post_date = models.DateField("Post date", default=timezone.now)
    description = MarkdownField(
        max_length=1024,
        blank=True,
        help_text=_(
            "Markdown-enabled summary text placed below the heading and title."
        ),
    )
    body = TutorialMarkdownField(
        blank=True, help_text=_("Markdown-enabled main content pane for this page.")
    )
    jumbotron = models.BooleanField(
        default=True,
        help_text=_(
            "Mark as true if this page should display its title and description in a jumbotron"
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("post_date"),
        FieldPanel("jumbotron"),
        FieldPanel("heading"),
        FieldPanel("description"),
        FieldPanel("body"),
        FieldPanel("template"),
        InlinePanel("navigation_links", label=_("Subnavigation Links")),
    ]

    search_fields = Page.search_fields + [
        index.FilterField("post_date"),
        index.SearchField("description", partial_match=True),
        index.SearchField("body", partial_match=True),
        index.SearchField("heading", partial_match=True),
    ]


class StreamPage(Page, NavigationMixin):
    template = models.CharField(max_length=128, default="home/stream_page.jinja")
    post_date = models.DateField("Post date", default=timezone.now)
    description = models.CharField(max_length=512, blank=True)

    body = StreamField(
        [
            ("heading", blocks.CharBlock(classname="full title")),
            ("paragraph", blocks.RichTextBlock()),
            ("image", ImageChooserBlock()),
            ("url", blocks.URLBlock(required=False)),
        ],
        use_json_field=True
    )

    content_panels = Page.content_panels + [
        FieldPanel("post_date"),
        FieldPanel("description"),
        FieldPanel("body"),
        InlinePanel("navigation_links", label=_("Subnavigation Links")),
    ]


class MarkdownPage(NavigationMixin, Page):
    heading = models.CharField(
        max_length=128,
        blank=True,
        help_text=_(
            "Large heading text placed on the blue background introduction header"
        ),
    )
    template = models.CharField(
        max_length=128,
        help_text=_(
            "Relative filesystem path to the template file to be used for this page "
            "(advanced usage only - the template must exist on the filesystem). If you change "
            "this, help text suggestions on placement of elements may no longer apply."
        ),
        default="home/markdown_page.jinja",
    )
    post_date = models.DateField("Post date", default=timezone.now)
    description = MarkdownField(
        max_length=1024,
        blank=True,
        help_text=_(
            "Markdown-enabled summary text placed below the heading and title."
        ),
    )
    body = MarkdownField(
        blank=True, help_text=_("Markdown-enabled main content pane for this page.")
    )
    jumbotron = models.BooleanField(
        default=True,
        help_text=_(
            "Mark as true if this page should display its title and description in a jumbotron"
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("post_date"),
        FieldPanel("jumbotron"),
        FieldPanel("heading"),
        FieldPanel("description"),
        FieldPanel("body"),
        FieldPanel("template"),
        InlinePanel("navigation_links", label=_("Subnavigation Links")),
    ]

    search_fields = Page.search_fields + [
        index.FilterField("post_date"),
        index.SearchField("description", partial_match=True),
        index.SearchField("body", partial_match=True),
        index.SearchField("heading", partial_match=True),
    ]


class ContactPage(NavigationMixin, Page):
    template = "home/about/contact.jinja"
    description = models.CharField(max_length=512, blank=True)

    def serve(self, request):
        from .forms import ContactForm

        if request.method == "POST":
            form = ContactForm(request=request, data=request.POST)
            if form.is_valid():
                form.save()
                return redirect("home:contact-sent")
        else:
            form = ContactForm(request)

        return render(
            request,
            self.template,
            {
                "page": self,
                "form": form,
            },
        )

    content_panels = Page.content_panels + [FieldPanel("description")]


class PlatformSnippetPlacement(models.Model):
    page = ParentalKey("home.PlatformIndexPage", related_name="platform_placements")
    platform = models.ForeignKey(Platform, related_name="+", on_delete=models.CASCADE)

    panels = [
        FieldPanel("platform"),
    ]

    def __str__(self):
        return "Snippet placement for {0}".format(self.platform.name)

    class Meta:
        verbose_name = "platform placement"
        verbose_name_plural = "platform placements"
        ordering = ["platform"]


class PlatformIndexPage(NavigationMixin, Page):
    template = "home/resources/frameworks.jinja"
    description = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        InlinePanel("platform_placements", label="Platforms"),
        InlinePanel("navigation_links", label=_("Subnavigation Links")),
    ]

    def get_platforms(self):
        # highlight featured platforms? allow the community to rank them.
        return self.platform_placements.order_by("platform__name").all()

    def get_context(self, request):
        context = super().get_context(request)
        # FIXME: add pagination
        context["platforms"] = self.get_platforms()
        return context


class JournalTag(TaggedItemBase):
    content_object = ParentalKey("home.Journal", related_name="tagged_journals")


@register_snippet
class Journal(index.Indexed, ClusterableModel):
    name = models.CharField(max_length=255)
    url = models.URLField()
    issn = models.CharField(
        max_length=16, blank=True, help_text=_("Linking ISSN-L for this Journal")
    )
    description = MarkdownField()
    tags = TaggableManager(through=JournalTag, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("url"),
        FieldPanel("issn"),
        FieldPanel("description", widget=forms.Textarea),
        FieldPanel("tags"),
    ]

    search_fields = [
        index.SearchField("name", partial_match=True),
        index.SearchField("description", partial_match=True),
        index.SearchField("issn"),
        index.RelatedFields(
            "tags",
            [
                index.SearchField("name", partial_match=True),
            ],
        ),
    ]

    def __lt__(self, other):
        if isinstance(other, Journal):
            return self.name < other.name
        raise TypeError("Unorderable types: {0} < {1}".format(Journal, type(other)))

    def __str__(self):
        return "{0} {1} {2}".format(self.name, self.url, self.issn)


class JournalSnippetPlacement(models.Model):
    page = ParentalKey("home.JournalIndexPage", related_name="journal_placements")
    journal = models.ForeignKey(Journal, related_name="+", on_delete=models.CASCADE)

    panels = [
        FieldPanel("journal"),
    ]

    class Meta:
        verbose_name = "journal placement"
        verbose_name_plural = "journal placements"
        ordering = ["journal"]


class JournalIndexPage(NavigationMixin, Page):
    template = "home/resources/journals.jinja"
    description = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        InlinePanel("journal_placements", label="Journals"),
        InlinePanel("navigation_links", label=_("Subnavigation Links")),
    ]


@register_snippet
class ConferenceTheme(models.Model):

    CATEGORIES = Choices("Panel", "Session")

    title = models.CharField(max_length=512)
    category = models.CharField(
        choices=CATEGORIES, default=CATEGORIES.Panel, max_length=16
    )
    description = MarkdownField()
    external_url = models.URLField(
        help_text=_("URL to this conference theme's (panel / session) Discourse topic")
    )
    page = ParentalKey("home.ConferencePage", related_name="themes")

    def add_presentations(self, presentations):
        """
        presentations must be a collection of dicts with the following keys:
        title, url, user_pk, contributors (optional)
        """
        for presentation in presentations:
            user_id = presentation["user_pk"]
            submitter = MemberProfile.objects.get(user__pk=user_id)
            conference_presentation, created = self.presentations.get_or_create(
                title=presentation["title"],
                external_url=presentation["url"],
                submitter=submitter,
            )
            contributors = presentation.get("contributors")
            if contributors:
                conference_presentation.contributors.set(
                    Contributor.objects.filter(user__pk__in=contributors)
                )
            else:
                conference_presentation.contributors.add(
                    Contributor.objects.get(user__pk=user_id)
                )
            conference_presentation.save()

    def __str__(self):
        return "{0} {1}".format(self.category, self.title)

    panels = [
        FieldPanel("title"),
        FieldPanel("category"),
        FieldPanel("description"),
        FieldPanel("external_url"),
        # InlinePanel('presentations')
    ]


class ConferencePresentation(models.Model):
    theme = models.ForeignKey(
        ConferenceTheme, related_name="presentations", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=512, help_text=_("Title of this presentation"))
    external_url = models.URLField(
        help_text=_("URL to this presentation's Discourse topic")
    )
    submitter = models.ForeignKey(MemberProfile, on_delete=models.PROTECT)
    contributors = models.ManyToManyField(
        Contributor, related_name="conference_presentation_contributors"
    )

    def markdown_contributors(self):
        """returns markdown formatted authors"""
        linked_authors = [
            "[{0}]({1})".format(c.get_full_name(), c.member_profile_url)
            for c in self.contributors.all()
        ]
        return ", ".join(linked_authors)

    def __str__(self):
        return self.title


class ConferencePage(Page):

    template = "home/conference/index.jinja"
    introduction = MarkdownField(help_text=_("Lead introduction to the conference"))
    content = MarkdownField(help_text=_("Conference main body content markdown text"))
    start_date = models.DateField()
    end_date = models.DateField()
    external_url = models.URLField(
        help_text=_(
            "URL to the top-level Discourse category topic for this conference."
        )
    )
    submission_deadline = models.DateField(null=True, blank=True)
    submission_information = MarkdownField(
        help_text=_(
            "Markdown formatted info on how to submit a presentation to the conference"
        )
    )

    @property
    def is_accepting_submissions(self):
        if self.submission_deadline:
            return date.today() < self.submission_deadline
        return False

    @property
    def is_open(self):
        return self.start_date <= date.today()

    @property
    def is_archived(self):
        return date.today() > self.end_date

    content_panels = Page.content_panels + [
        FieldPanel("start_date"),
        FieldPanel("end_date"),
        FieldPanel("introduction"),
        FieldPanel("content"),
        FieldPanel("external_url"),
        FieldPanel("submission_deadline"),
        FieldPanel("submission_information"),
        InlinePanel("themes", label="Themes"),
    ]


class ConferenceIndexPage(Page, NavigationMixin):

    template = "home/conference/list.jinja"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("slug", "conference")
        super().__init__(*args, **kwargs)

    def conferences(self):
        return ConferencePage.objects.live().descendant_of(self)

    content_panels = Page.content_panels


class ConferenceSubmission(models.Model):
    submitter = models.ForeignKey(MemberProfile, on_delete=models.DO_NOTHING)
    presenters = models.ManyToManyField(Contributor)
    conference = models.ForeignKey(
        ConferencePage, related_name="submissions", on_delete=models.PROTECT
    )
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=150, help_text=_("Presentation title"))
    abstract = MarkdownField(
        max_length=3000, help_text=_("Presentation abstract"), blank=False
    )
    video_url = models.URLField(help_text=_("URL to your video presentation"))
    model_url = models.URLField(
        help_text=_(
            "Persistent URL to a model associated with your presentation (if applicable)"
        ),
        blank=True,
    )

    def __str__(self):
        return "submission {} by {}".format(self.title, self.submitter)


@register_snippet
class FaqEntry(index.Indexed, models.Model):
    FAQ_CATEGORIES = Choices(
        ("abm", _("Agent-based Modeling Questions")),
        ("general", _("General CoMSES Net Questions")),
        ("model-library", _("Computational Model Library Questions")),
    )
    category = models.CharField(
        max_length=32, choices=FAQ_CATEGORIES, default=FAQ_CATEGORIES.general
    )
    question = models.CharField(max_length=128, help_text=_("Short question"))
    answer = models.TextField(help_text=_("Markdown formatted answer"))
    date_created = models.DateTimeField(auto_now=True)
    last_modified = models.DateTimeField(auto_now_add=True)
    submitter = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.SET_NULL
    )

    search_fields = [
        index.SearchField("category"),
        index.SearchField("question"),
        index.SearchField("answer"),
        index.FilterField("date_created"),
        index.FilterField("last_modified"),
    ]

    def __str__(self):
        return "[{0}] {1} {2}".format(
            self.category, self.question, shorten(self.answer, 140)
        )


class FaqEntryPlacement(models.Model):
    page = ParentalKey("home.FaqPage", related_name="faq_entry_placements")
    faq_entry = models.ForeignKey(FaqEntry, related_name="+", on_delete=models.CASCADE)

    panels = [
        FieldPanel("faq_entry"),
    ]

    class Meta:
        verbose_name = "faq placement"


class FaqPage(Page, NavigationMixin):
    template = "home/about/faq.jinja"
    description = models.CharField(max_length=1000)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # FIXME: add pagination
        context["faq_entries"] = FaqEntry.objects.all()
        context["faq_categories"] = FaqEntry.FAQ_CATEGORIES
        return context

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        InlinePanel("faq_entry_placements", label="FAQ Entries"),
    ]

    def get_faq_entry_questions(self):
        return "\n".join(FaqEntry.objects.values_list("question", flat=True))

    def get_faq_entry_answers(self):
        return "\n".join(FaqEntry.objects.values_list("answer", flat=True))

    search_fields = Page.search_fields + [
        index.SearchField("description", partial_match=True),
        index.SearchField("get_faq_entry_questions", partial_match=True),
        index.SearchField("get_faq_entry_answers", partial_match=True),
    ]


class PeopleEntryPlacementQuerySet(models.QuerySet):
    def board(self, **kwargs):
        return self.filter(category=PeopleEntryPlacement.CATEGORIES.board, **kwargs)

    def digest(self, **kwargs):
        return self.filter(category=PeopleEntryPlacement.CATEGORIES.digest, **kwargs)

    def digest_member_profiles(self, **kwargs):
        return MemberProfile.objects.filter(
            pk__in=self.digest(**kwargs).values_list("member_profile", flat=True)
        )

    def update_sort_order_alpha(self):
        for idx, pep in enumerate(self.order_by("member_profile__user__last_name")):
            pep.sort_order = idx
            pep.save()


@register_snippet
class PeopleEntryPlacement(Orderable, models.Model):
    CATEGORIES = Choices(
        (1, "directorate", _("Directorate")),
        (2, "board", _("Executive Board")),
        (3, "digest", _("CoMSES Digest Editors")),
        (4, "infrastructure", _("Infrastructure Group")),
        (5, "alumni", _("Executive Board Alumni")),
    )
    page = ParentalKey("home.PeoplePage", related_name="people_entry_placements")
    member_profile = models.ForeignKey(
        "core.MemberProfile", related_name="+", on_delete=models.CASCADE
    )
    category = models.PositiveIntegerField(choices=CATEGORIES, default=CATEGORIES.board)
    term = models.CharField(
        blank=True,
        max_length=64,
        help_text=_(
            "The term for a given board member (e.g., 2016-2018 or 2008-2010, 2014-2016)"
        ),
    )

    objects = PeopleEntryPlacementQuerySet.as_manager()

    panels = [
        FieldPanel("member_profile"),
        FieldPanel("category"),
        FieldPanel("term"),
    ]

    @property
    def is_board_member(self):
        return self.category in (self.CATEGORIES.board, self.CATEGORIES.alumni)

    def __str__(self):
        return "{0}: {1} {2}".format(
            self.sort_order, self.member_profile, self.category
        )

    class Meta:
        verbose_name = "people entry placement"


class PeoplePage(Page, NavigationMixin):
    template = "home/about/people.jinja"
    heading = models.CharField(max_length=64)
    description = MarkdownField(
        help_text=_("Text blurb on the people leading comses.net")
    )

    def sort_board(self):
        PeopleEntryPlacement.objects.board().update_sort_order_alpha()

    def add_users(self, category, usernames, offset):
        for idx, username in enumerate(usernames):
            # manually iterate and get MemberProfile to enforce original ordering
            profile = MemberProfile.objects.get(user__username=username)
            self.people_entry_placements.add(
                PeopleEntryPlacement(
                    sort_order=offset + idx, member_profile=profile, category=category
                )
            )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["people_categories"] = PeopleEntryPlacement.CATEGORIES
        return context

    content_panels = Page.content_panels + [
        FieldPanel("heading"),
        FieldPanel("description"),
        InlinePanel("people_entry_placements", label="People Entries"),
    ]


class NewsIndexPage(Page):
    def get_context(self, request):
        context = super(NewsIndexPage, self).get_context(request)
        context["news_entries"] = NewsPage.objects.child_of(self).live()
        return context


class NewsPage(Page):
    body = RichTextField()
    post_date = models.DateField("Post date")
    feed_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    search_fields = Page.search_fields + [
        index.FilterField("post_date"),
        index.SearchField("body", partial_match=True),
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel("post_date"),
        FieldPanel("body", classname="full"),
        InlinePanel("related_links", label="Related links"),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
        FieldPanel("feed_image"),
    ]

    # Parent page / subpage type rules
    parent_page_types = ["home.NewsIndexPage"]
    subpage_types = []


class NewsPageRelatedLink(Orderable):
    page = ParentalKey(NewsPage, related_name="related_links")
    name = models.CharField(max_length=255)
    url = models.URLField()

    panels = [
        FieldPanel("name"),
        FieldPanel("url"),
    ]
