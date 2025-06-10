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
from django.utils.translation import gettext_lazy as _
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
from django.urls import reverse

from core.fields import MarkdownField, TutorialMarkdownField
from core.fs import get_canonical_image
from core.models import MemberProfile, Platform, Event, Job
from core.widgets import MarkdownTextarea

# FIXME: should these models be pushed into core..
from library.models import CodebaseRelease, Contributor

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

    mission_statement = models.CharField(max_length=512)
    community_statement = models.TextField()

    def get_featured_content(self):
        return self.featured_content_queue.select_related(
            "image", "codebase_image", "link_codebase", "link_page"
        ).all()[: self.FEATURED_CONTENT_COUNT]

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
        context["feed_urls"] = {
            "reviewed_models": reverse("home:reviewed-model-feed"),
            "events": reverse("home:event-feed"),
            "forum": reverse("home:forum-feed"),
            "forum_categories": reverse("home:forum-categories-feed"),
            "jobs": reverse("home:job-feed"),
            "youtube": reverse("home:youtube-feed"),
        }
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
        return f"CategoryIndexItem: {self.title} {self.url}"


class SubnavigationMenu:
    pass


class SubNavigationLink(Orderable, models.Model):
    page = ParentalKey(Page, related_name="navigation_links")
    url = models.CharField("Relative path, absolute path, or full URL", max_length=255)
    title = models.CharField(max_length=128)

    def __str__(self):
        return f"SubNavigationLink: {self.page} {self.title} ({self.url})"


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
            user = User.get_anonymous()
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

    search_fields = Page.search_fields + [index.SearchField("summary")]


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
        self,
        image_path,
        title,
        summary,
        category,
        tags=None,
        sort_order=None,
        user=None,
        url="",
    ):
        if self.cards.filter(title=title):
            return
        if user is None:
            user = User.get_anonymous()
        _image = (
            get_canonical_image(title=title, path=image_path, user=user)
            if image_path
            else None
        )
        card = TutorialCard(
            title=title,
            sort_order=sort_order,
            summary=summary,
            category=category,
            thumbnail_image=_image,
            url=url,
        )
        for tag in tags:
            card.tags.add(tag)
        self.cards.add(card)

    content_panels = Page.content_panels + [
        FieldPanel("heading"),
        FieldPanel("summary", widget=MarkdownTextarea),
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
        context["categories"] = TutorialCard.EducationalContentCategory.choices
        context["jumbotron"] = self.jumbotron_dict
        return context

    @property
    def jumbotron_dict(self):
        return TutorialCard.EducationalContentCategory.jumbotron_dict()


class TutorialTag(TaggedItemBase):
    content_object = ParentalKey("TutorialCard", related_name="tagged_items")


class TutorialCard(Orderable, ClusterableModel):
    """Content cards displayed in the Education Page"""

    class EducationalContentCategory(models.TextChoices):
        IN_HOUSE = ("in-house", _("CoMSES"))
        PARTNER = ("partner", _("Partners"))
        COMMUNITY = ("community", _("Open Science Community"))

        @classmethod
        def jumbotron_dict(cls):
            return {
                cls.IN_HOUSE: _(
                    """CoMSES Net training modules provide guidance on good practices for computational modeling and sharing your work with [FAIR principles for research software (FAIR4RS)](https://doi.org/10.15497/RDA00068) and general [good enough practices for scientific computation](https://carpentries-lab.github.io/good-enough-practices/) in mind.\n\nOur [education forum](https://forum.comses.net/c/education) also hosts a [community curated list of additional educational resources](https://forum.comses.net/t/educational-resources/9159/2) and can be freely used to discuss, collaborate, and share additional educational resources.
                    """
                ),
                cls.PARTNER: _(
                    """Educational resources produced by our partners and collaborators, [Community Surface Dynamics Modeling System (CSDMS)](https://csdms.colorado.edu/wiki/Main_Page) and [CUAHSI](https://www.cuahsi.org/)."""
                ),
                cls.COMMUNITY: _(
                    """Educational content from the broader open science community."""
                ),
            }

    category = models.CharField(
        choices=EducationalContentCategory.choices,
        default=EducationalContentCategory.IN_HOUSE,
        max_length=32,
    )
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
        FieldPanel("summary", widget=MarkdownTextarea),
        FieldPanel("thumbnail_image"),
        FieldPanel("tags"),
    ]

    def __str__(self):
        return f"TutorialCard: {self.title} {self.url}"


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
        index.SearchField("description"),
        index.SearchField("body"),
        index.SearchField("heading"),
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
        use_json_field=True,
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
        index.SearchField("description"),
        index.SearchField("body"),
        index.SearchField("heading"),
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
        return f"Snippet placement for {self.platform.name}"

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
        index.SearchField("name"),
        index.SearchField("description"),
        index.SearchField("issn"),
        index.RelatedFields(
            "tags",
            [
                index.SearchField("name"),
            ],
        ),
    ]

    def __lt__(self, other):
        if isinstance(other, Journal):
            return self.name < other.name
        raise TypeError(f"Unorderable types: {Journal} < {type(other)}")

    def __str__(self):
        return f"{self.name} {self.url} {self.issn}"


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
    class Categories(models.TextChoices):
        PANEL = "Panel", _("Panel")
        SESSION = "Session", _("Session")

    title = models.CharField(max_length=512)
    category = models.CharField(
        choices=Categories.choices, default=Categories.PANEL, max_length=16
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
        return f"ConferenceTheme: {self.category} {self.title}"

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
        linked_authors = [c.get_markdown_link() for c in self.contributors.all()]
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
        if not args:
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
        return f"ConferenceSubmission {self.title} {self.submitter}"


@register_snippet
class ComsesDigest(index.Indexed, models.Model):
    """
    represents a single issue of the quarterly digest that points to a static pdf file
    """

    class Seasons(models.IntegerChoices):
        SPRING = 1, _("Spring")
        SUMMER = 2, _("Summer")
        FALL = 3, _("Fall")
        WINTER = 4, _("Winter")

    contributors = models.ManyToManyField(Contributor)
    doi = models.CharField(max_length=128, unique=True, blank=True, null=True)
    season = models.IntegerField(choices=Seasons.choices)
    volume = models.IntegerField()
    issue_number = models.IntegerField()
    publication_date = models.DateField()
    static_path = models.CharField(max_length=128, unique=True)

    @property
    def year_published(self):
        return self.publication_date.year

    @property
    def title(self):
        return f"CoMSES Digest: {self.get_season_display()} {self.year_published}"

    def get_volume_issue_display(self):
        return f"Vol. {self.volume}, No. {self.issue_number}"

    def get_formatted_publication_date(self):
        return self.publication_date.strftime("%B %d, %Y")

    def __str__(self):
        return f"{self.title}, {self.get_volume_issue_display()}"

    class Meta:
        ordering = ["-volume", "-issue_number"]


@register_snippet
class FaqEntry(index.Indexed, models.Model):
    class Categories(models.TextChoices):
        ABM = "abm", _("Agent-based Modeling Questions")
        GENERAL = "general", _("General CoMSES Net Questions")
        MODEL_LIBRARY = "model-library", _("Computational Model Library Questions")

    category = models.CharField(
        max_length=32, choices=Categories.choices, default=Categories.GENERAL
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
        return f"[{self.category}] {self.question} {shorten(self.answer, 140)}"


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
        context["faq_categories"] = FaqEntry.Categories
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
        index.SearchField("description"),
        index.SearchField("get_faq_entry_questions"),
        index.SearchField("get_faq_entry_answers"),
    ]


class PeopleEntryPlacementQuerySet(models.QuerySet):
    def board(self, **kwargs):
        return self.filter(
            category=PeopleEntryPlacement.Categories.EXECUTIVE_BOARD, **kwargs
        )

    def digest(self, **kwargs):
        return self.filter(category=PeopleEntryPlacement.Categories.DIGEST, **kwargs)

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
    class Categories(models.IntegerChoices):
        DIRECTORATE = 1
        EXECUTIVE_BOARD = 2
        DIGEST_EDITORS = 3
        INFRASTRUCTURE_GROUP = 4
        EXECUTIVE_BOARD_ALUMNI = 5

    page = ParentalKey("home.PeoplePage", related_name="people_entry_placements")
    member_profile = models.ForeignKey(
        "core.MemberProfile", related_name="+", on_delete=models.CASCADE
    )
    category = models.PositiveIntegerField(
        choices=Categories.choices, default=Categories.EXECUTIVE_BOARD
    )
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
        return self.category in {
            self.Categories.EXECUTIVE_BOARD,
            self.Categories.EXECUTIVE_BOARD_ALUMNI,
        }

    def __str__(self):
        return f"{self.sort_order}: {self.member_profile} {self.category.label}"

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
        context["people_categories"] = PeopleEntryPlacement.Categories
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
        index.SearchField("body"),
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
